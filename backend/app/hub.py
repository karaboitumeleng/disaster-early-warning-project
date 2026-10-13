import logging
from typing import Any

from fastapi import WebSocket

log = logging.getLogger(__name__)


class AlertHub:
    def __init__(self) -> None:
        self._conns: set[WebSocket] = set()

    def connect(self, ws: WebSocket) -> None:
        self._conns.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._conns.discard(ws)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for ws in list(self._conns):
            try:
                await ws.send_json(message)
            except Exception:
                self._conns.discard(ws)

    async def close_all(self) -> None:
        for ws in list(self._conns):
            try:
                await ws.close(code=1001)  # going away: clean close on shutdown
            except Exception:
                log.debug("ws already closed")
        self._conns.clear()