"""
app/core/websocket.py
Real-time WebSocket connection manager with strict multi-tenant isolation.
Ensures events for Factory A are only broadcast to clients belonging to Factory A.
"""
import asyncio
from datetime import datetime
import json
from typing import Any, Dict, Iterable, List, Optional, Set
import uuid

from fastapi import WebSocket

from .logging import logger


class CustomJSONEncoder(json.JSONEncoder):
    """Encodes UUIDs and datetimes to standard ISO strings for WebSockets."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class WebSocketConnectionManager:
    """
    Manages active WebSocket sessions partitioned strictly by tenant factory_id.
    Guarantees cross-tenant isolation: clients never receive events from other factories.

    Shutdown lifecycle
    ------------------
    Call ``await close_all()`` from the application lifespan shutdown handler.
    ``close_all()`` does not return until every tracked handler and revalidation
    task has finished or been cancelled and awaited. Redis must not be closed
    until that return.

    Task registration
    -----------------
    Register both the connection handler and its membership-revalidation task.
    A done-callback removes the task as soon as it finishes, including when the
    task is already done at registration time, so the set cannot keep a stale
    reference.
    """

    def __init__(self) -> None:
        # factory_id -> Set[WebSocket]
        self._active_connections: Dict[uuid.UUID, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

        # Live handler and revalidation tasks. A done-callback removes each one.
        # Snapshots are plain copies taken without awaiting, so the set cannot
        # change while it is being read.
        self._handler_tasks: Set[asyncio.Task] = set()

        # Set by close_all() to signal handlers that shutdown has begun.
        # Handlers should check this flag in their receive/revalidation loops.
        self._shutdown_event = asyncio.Event()

    # ── Task registration ─────────────────────────────────────────────────────

    def register_handler_task(self, task: asyncio.Task) -> None:
        """
        Register a handler task so close_all() can track and cancel it.

        A done-callback is installed immediately so the task is removed from
        the set as soon as it completes — preventing stale references even if
        close_all() is never called (e.g. client disconnects normally).

        Must be called from within the task itself:
            task = asyncio.current_task()
            ws_manager.register_handler_task(task)

        The task is added before the done-callback is installed. If it has
        already finished, asyncio runs the callback immediately and the task
        is discarded before this method returns. A second discard covers a
        task that finished as the callback was attached, so a finished task
        cannot remain in the set.
        """
        self._handler_tasks.add(task)
        try:
            task.add_done_callback(self._discard_handler_task)
        except Exception:
            self._handler_tasks.discard(task)
            raise
        if task.done():
            self._handler_tasks.discard(task)

    def _discard_handler_task(self, task: asyncio.Task) -> None:
        """Remove a finished task. Safe to run more than once."""
        self._handler_tasks.discard(task)

    def _snapshot_handler_tasks(self) -> tuple[asyncio.Task, ...]:
        """Copy tracked tasks, excluding the task that is running close_all().

        The copy is a tuple taken synchronously. Awaiting the current task
        would deadlock, so that task is never part of the snapshot.
        """
        current = asyncio.current_task()
        stable = tuple(self._handler_tasks)
        return tuple(task for task in stable if task is not current)

    def _log_task_exception(self, task: asyncio.Task) -> None:
        """Log an exception stored on a finished task.

        Cancelled tasks are expected during shutdown and are not logged.
        """
        if not task.done() or task.cancelled():
            return
        try:
            exc = task.exception()
        except (asyncio.CancelledError, asyncio.InvalidStateError):
            return
        if exc is not None:
            logger.error(
                f"close_all: handler task {task.get_name()!r} "
                f"raised {type(exc).__name__}: {exc}"
            )

    # ── Graceful shutdown ─────────────────────────────────────────────────────

    async def close_all(self, timeout: float = 10.0) -> None:
        """
        Signal all handlers to stop and close every active WebSocket.

        Steps (in order):
          1. Set _shutdown_event so handlers notice shutdown in their loops.
          2. Snapshot active sockets and close them before waiting on tasks.
          3. Snapshot tracked handler and revalidation tasks, excluding the
             current task so close_all() never awaits itself.
          4. Wait up to ``timeout`` seconds for those tasks to finish.
          5. Cancel tasks that are still pending after the timeout.
          6. Await cancellation with return_exceptions=True.
          7. Repeat: snapshot, cancel, and await any task registered during
             shutdown. Return only when a fresh snapshot has no pending task
             other than the task running close_all(). If tasks are still
             pending after repeated cancellation, raise so the caller does
             not close Redis.
          8. Retrieve and log exceptions from tasks that finished on their own.

        Redis lifecycle:
          This method returns only after every tracked handler and revalidation
          task has finished or been cancelled and awaited. The lifespan handler
          must close Redis only after this method returns:
              await ws_manager.close_all()
              await app.state.redis.aclose()
        """
        self._shutdown_event.set()

        async with self._lock:
            socket_snapshot: List[WebSocket] = [
                ws
                for sockets in self._active_connections.values()
                for ws in list(sockets)
            ]

        for ws in socket_snapshot:
            try:
                await ws.close(code=1001, reason="server_shutdown")
            except Exception as exc:
                logger.debug(f"close_all: error closing socket during shutdown: {exc}")

        task_snapshot = self._snapshot_handler_tasks()
        pending = [task for task in task_snapshot if not task.done()]
        finished: Set[asyncio.Task] = {task for task in task_snapshot if task.done()}

        if pending:
            done, still_pending = await asyncio.wait(pending, timeout=timeout)
            finished.update(done)
        else:
            still_pending = set()

        for task in still_pending:
            task.cancel()
        if still_pending:
            await asyncio.gather(*still_pending, return_exceptions=True)

        # A handler can register its revalidation task while sockets are
        # closing, during the grace period, or from a cancellation handler.
        # Each pass takes a new stable snapshot, cancels what is still
        # pending, and awaits that cancellation. This returns only when a
        # snapshot contains no pending task besides the one running close_all.
        late_pending: List[asyncio.Task] = []
        for _ in range(32):
            newcomers = [task for task in self._snapshot_handler_tasks() if not task.done()]
            if not newcomers:
                break
            late_pending.extend(newcomers)
            for task in newcomers:
                if task is asyncio.current_task() or task.done():
                    continue
                task.cancel()
            await asyncio.gather(*newcomers, return_exceptions=True)
        else:
            survivors = [task for task in self._snapshot_handler_tasks() if not task.done()]
            if survivors:
                raise RuntimeError(
                    "close_all: tracked handler tasks are still running after "
                    "cancellation. Redis must not be closed."
                )

        for task in list(finished) + list(still_pending) + late_pending:
            self._log_task_exception(task)

        survivors = [task for task in self._snapshot_handler_tasks() if not task.done()]
        if survivors:
            raise RuntimeError(
                "close_all: tracked handler tasks are still running after "
                "cancellation. Redis must not be closed."
            )

        logger.info(
            f"close_all: shutdown complete — "
            f"{len(socket_snapshot)} socket(s) closed, "
            f"{len(task_snapshot) + len(late_pending)} task(s) awaited."
        )

    async def register_accepted(self, websocket: WebSocket, factory_id: uuid.UUID) -> None:
        """
        Register an already-accepted WebSocket without calling accept() again.

        Used by the ticket-auth endpoint where accept() is called explicitly
        after all authentication checks pass.  The legacy ``connect()`` method
        calls accept() itself, which is correct for the old human-JWT flow.
        """
        async with self._lock:
            if factory_id not in self._active_connections:
                self._active_connections[factory_id] = set()
            self._active_connections[factory_id].add(websocket)

        logger.info(
            f"WS ticket client registered. Factory: {factory_id}. "
            f"Active connections for factory: {len(self._active_connections[factory_id])}"
        )

    async def connect(self, websocket: WebSocket, factory_id: uuid.UUID) -> None:
        """Accept incoming connection and register under the tenant factory_id."""
        await websocket.accept()
        async with self._lock:
            if factory_id not in self._active_connections:
                self._active_connections[factory_id] = set()
            self._active_connections[factory_id].add(websocket)

        logger.info(
            f"WebSocket client connected. Factory: {factory_id}. "
            f"Active connections for factory: {len(self._active_connections[factory_id])}"
        )

    async def disconnect(self, websocket: WebSocket, factory_id: uuid.UUID) -> None:
        """Unregister closed connection and clean up empty tenant buckets."""
        async with self._lock:
            if factory_id in self._active_connections:
                self._active_connections[factory_id].discard(websocket)
                if not self._active_connections[factory_id]:
                    del self._active_connections[factory_id]

        logger.info(f"WebSocket client disconnected. Factory: {factory_id}.")

    async def broadcast_to_factory(
        self,
        factory_id: uuid.UUID,
        message: Dict[str, Any],
    ) -> int:
        """
        Broadcast JSON payload to all active clients of a specific factory.
        Returns the number of clients successfully notified.
        """
        async with self._lock:
            connections = list(self._active_connections.get(factory_id, []))

        if not connections:
            return 0

        payload_text = json.dumps(message, cls=CustomJSONEncoder)
        dead_connections = []
        sent_count = 0

        for ws in connections:
            try:
                await ws.send_text(payload_text)
                sent_count += 1
            except Exception as exc:
                logger.warning(f"Error sending to WebSocket client in factory {factory_id}: {exc}")
                dead_connections.append(ws)

        # Clean up any dead connections
        if dead_connections:
            async with self._lock:
                if factory_id in self._active_connections:
                    for dead_ws in dead_connections:
                        self._active_connections[factory_id].discard(dead_ws)
                    if not self._active_connections[factory_id]:
                        del self._active_connections[factory_id]

        return sent_count

    def get_active_count(self, factory_id: Optional[uuid.UUID] = None) -> int:
        """Get count of active connections for a specific factory or globally."""
        if factory_id is not None:
            return len(self._active_connections.get(factory_id, set()))
        return sum(len(conns) for conns in self._active_connections.values())


# Global singleton instance
ws_manager = WebSocketConnectionManager()
