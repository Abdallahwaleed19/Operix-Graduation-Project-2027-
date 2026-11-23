"""
Shutdown behavior of WebSocketConnectionManager.

No Redis client is opened and no WebSocket ticket is issued.
"""
import asyncio
import logging
import uuid

from app.core.websocket import WebSocketConnectionManager


class _Socket:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.events.append(f"socket:{code}")


def test_close_all_closes_sockets_then_drains_tasks(caplog):
    events: list[str] = []
    manager = WebSocketConnectionManager()
    socket = _Socket(events)
    factory_id = uuid.uuid4()

    async def finishes() -> None:
        events.append("handler-start")
        await asyncio.sleep(0.05)
        events.append("handler-done")

    async def hangs() -> None:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            events.append("revalidation-cancelled")
            raise

    async def fails() -> None:
        await asyncio.sleep(0.01)
        raise RuntimeError("handler failed")

    async def runner() -> None:
        async with manager._lock:
            manager._active_connections[factory_id] = {socket}

        handler = asyncio.create_task(finishes(), name="handler")
        revalidation = asyncio.create_task(hangs(), name="revalidate")
        broken = asyncio.create_task(fails(), name="broken")
        manager.register_handler_task(handler)
        manager.register_handler_task(revalidation)
        manager.register_handler_task(broken)

        finished = asyncio.create_task(asyncio.sleep(0), name="already-done")
        await finished
        manager.register_handler_task(finished)
        assert finished not in manager._handler_tasks

        current = asyncio.current_task()
        assert current is not None
        manager.register_handler_task(current)

        with caplog.at_level(logging.ERROR):
            await asyncio.wait_for(manager.close_all(timeout=0.2), timeout=2)

        assert "socket:1001" in events
        assert events.index("socket:1001") < events.index("handler-done")
        assert "revalidation-cancelled" in events
        assert handler.done() and not handler.cancelled()
        assert revalidation.cancelled()
        assert broken.done()
        assert not current.done()
        assert finished not in manager._handler_tasks
        assert handler not in manager._handler_tasks
        assert revalidation not in manager._handler_tasks
        assert broken not in manager._handler_tasks
        assert any("handler failed" in record.message for record in caplog.records)

    asyncio.run(runner())


def test_close_all_drains_tasks_spawned_by_cancellation():
    """A task cancelled during shutdown may register another task.

    close_all must not return, and Redis must not be closed, while any
    tracked handler other than the caller is still running.
    """
    events: list[str] = []
    manager = WebSocketConnectionManager()

    async def chain(remaining: int) -> None:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            events.append(f"cancel-{remaining}")
            if remaining > 0:
                child = asyncio.create_task(chain(remaining - 1), name=f"child-{remaining}")
                manager.register_handler_task(child)
            raise

    async def runner() -> None:
        current = asyncio.current_task()
        assert current is not None
        manager.register_handler_task(current)
        root = asyncio.create_task(chain(4), name="root")
        manager.register_handler_task(root)

        redis_closed: list[str] = []

        await asyncio.wait_for(manager.close_all(timeout=0.05), timeout=3)
        pending = [task for task in manager._handler_tasks if task is not current and not task.done()]
        assert pending == []
        redis_closed.append("closed")

        assert redis_closed == ["closed"]
        assert not current.done()
        assert root.done()
        assert [events.count(f"cancel-{level}") for level in range(5)] == [1, 1, 1, 1, 1]
        assert all(task.done() for task in manager._handler_tasks if task is not current)

    asyncio.run(runner())
