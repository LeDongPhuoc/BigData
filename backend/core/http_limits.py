"""Bound admission and body reads before JSON parsing, including chunked requests."""

import asyncio

from starlette.responses import JSONResponse


class RequestLimits:
    def __init__(self, app, *, body_limit=128 * 1024, active_limit=16, body_seconds=5):
        self.app = app
        self.body_limit, self.active_limit, self.body_seconds = (
            body_limit,
            active_limit,
            body_seconds,
        )
        self.active = 0

    async def reject(self, scope, receive, send, status, code):
        request_id = scope["state"]["request_id"]
        response = JSONResponse(
            status_code=status,
            headers={"X-Request-ID": request_id, "Cache-Control": "no-store"},
            content={
                "error": {
                    "code": code,
                    "message": "Request unavailable",
                    "request_id": request_id,
                    "details": [],
                }
            },
        )
        await response(scope, receive, send)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        # ASGI requests share one event loop per worker. No await separates this check
        # and increment, so admission cannot race. Includes clients still sending bodies.
        if self.active >= self.active_limit:
            await self.reject(scope, receive, send, 503, "server_busy")
            return
        self.active += 1
        try:
            lengths = [v for k, v in scope["headers"] if k.lower() == b"content-length"]
            if lengths:
                if len(lengths) != 1 or len(lengths[0]) > 12 or not lengths[0].isdigit():
                    await self.reject(scope, receive, send, 400, "invalid_content_length")
                    return
                if int(lengths[0]) > self.body_limit:
                    await self.reject(scope, receive, send, 413, "request_too_large")
                    return
            body_buffer, size = bytearray(), 0
            deadline = asyncio.get_running_loop().time() + self.body_seconds
            while True:
                try:
                    message = await asyncio.wait_for(
                        receive(), max(0, deadline - asyncio.get_running_loop().time())
                    )
                except asyncio.TimeoutError:
                    await self.reject(scope, receive, send, 408, "body_timeout")
                    return
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > self.body_limit:
                    await self.reject(scope, receive, send, 413, "request_too_large")
                    return
                body_buffer.extend(chunk)
                if not message.get("more_body", False):
                    break
            body = bytes(body_buffer)
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if delivered:
                    return await receive()
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}

            await self.app(scope, bounded_receive, send)
        finally:
            self.active -= 1
