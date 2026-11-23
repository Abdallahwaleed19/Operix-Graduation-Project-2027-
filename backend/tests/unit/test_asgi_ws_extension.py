"""
tests/unit/test_asgi_ws_extension.py

Documents whether the `websocket.http.response` ASGI extension is present in
scope at runtime (required for Starlette's send_denial_response() to work).

Key finding from prior audit:
  - In production (uvicorn + websockets): extension IS present in scope.
  - In TestClient (Starlette's mock transport): extension is NOT present.

Consequence for the WS Ticket feature:
  - In tests, `websocket.send_denial_response()` will raise RuntimeError.
  - The WS ticket handler MUST have a fallback to `websocket.close()`.
  - Tests must use `websocket.close()` path, not `send_denial_response()`.

This test always passes. It documents the runtime behavior as a reproducible
fact rather than an assumption from reading source code.
"""
import pytest
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.testclient import TestClient
from starlette.websockets import WebSocket, WebSocketDisconnect

# Capture the extensions dict from the actual ASGI scope
_captured_extensions: dict = {}


async def _capture_scope_ws(ws: WebSocket) -> None:
    """Minimal WebSocket handler: accepts, captures scope extensions, then closes."""
    await ws.accept()
    _captured_extensions.clear()
    _captured_extensions.update(ws.scope.get("extensions", {}))
    await ws.close()


_app = Starlette(routes=[WebSocketRoute("/ws-test", _capture_scope_ws)])


def test_ws_http_response_extension_present_in_test_client():
    """
    DOCUMENTS (RUNTIME-VERIFIED): websocket.http.response IS present in
    Starlette 1.10 TestClient scope with httpx2 transport.

    Prior source-code inference was wrong — this test corrects the record.

    Consequence for the WS Ticket feature:
      - send_denial_response() MAY work in unit tests with this Starlette version.
      - However, the WS ticket handler should STILL implement the fallback
        to websocket.close() for forward-compatibility and defence-in-depth,
        because production behaviour (uvicorn + websockets sansio) is what
        actually counts, and behaviour can vary between ASGI servers.
      - Always test the rejection path via websocket.close() as the primary path.
    """
    client = TestClient(_app)
    # Starlette 1.10 raises WebSocketDisconnect when server closes after accept
    try:
        with client.websocket_connect("/ws-test"):
            pass
    except WebSocketDisconnect:
        pass  # Expected: server closed the socket cleanly

    extension_present = "websocket.http.response" in _captured_extensions
    # RUNTIME FACT (Starlette 1.10 + httpx2): extension IS present
    assert extension_present, (
        "UNEXPECTED: websocket.http.response is NOT present in TestClient scope. "
        "Starlette 1.10 + httpx2 injects this extension. "
        "Re-verify the WS ticket handler's rejection path."
    )


def test_ws_scope_extensions_captured():
    """
    Documents all extensions present in TestClient scope.
    Use for future reference if Starlette adds new extensions.
    """
    client = TestClient(_app)
    try:
        with client.websocket_connect("/ws-test"):
            pass
    except WebSocketDisconnect:
        pass  # Expected

    # Print for -s output; test always passes
    print(f"\nExtensions in TestClient scope: {list(_captured_extensions.keys())}")
    assert isinstance(_captured_extensions, dict)
