"""Bound multipart ingress before framework spooling, including chunked bodies."""

from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class UploadLimit:
    def __init__(
        self, app: ASGIApp, max_bytes: int, meeting_max_bytes: int = 65536
    ) -> None:
        self.app, self.max_bytes = app, max_bytes + 65536
        self.meeting_max_bytes = meeting_max_bytes + 65536

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] not in (
            "/api/documents/upload",
            "/api/meetings/upload",
        ):
            await self.app(scope, receive, send)
            return
        buffer = bytearray()
        meeting = scope["path"] == "/api/meetings/upload"
        maximum = self.meeting_max_bytes if meeting else self.max_bytes
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            buffer.extend(message.get("body", b""))
            if len(buffer) > maximum:
                request_id = scope.get("state", {}).get("request_id", str(uuid4()))
                response = JSONResponse(
                    {
                        "code": "TXT_SIZE_LIMIT" if meeting else "PDF_SIZE_LIMIT",
                        "message": "Upload exceeds the configured file limit.",
                        "request_id": request_id,
                    },
                    status_code=413,
                    headers={"X-Request-ID": request_id},
                )
                await response(scope, receive, send)
                return
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {
                    "type": "http.request",
                    "body": bytes(buffer),
                    "more_body": False,
                }
            return await receive()

        await self.app(scope, replay, send)
