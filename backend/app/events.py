import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.schemas import WeatherReading

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DataIngested:
    reading: WeatherReading
    reading_hash: str
    received_at: float  # time.monotonic() when the API accepted the payload


Handler = Callable[[Any], Awaitable[None]]


class EventBus:
    """In-process async pub/sub. Handlers are isolated: one failing never affects the publisher."""

    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)
        self._tasks: set[asyncio.Task[None]] = set()

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: object) -> None:
        for handler in self._handlers[type(event)]:
            task = asyncio.create_task(self._safe(handler, event))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _safe(self, handler: Handler, event: object) -> None:
        try:
            await handler(event)
        except Exception:
            log.exception("event handler failed", extra={"ctx": {"event": type(event).__name__}})

    async def drain(self, timeout: float = 10.0) -> None:
        """Graceful shutdown: let in-flight handlers finish."""
        if self._tasks:
            await asyncio.wait(set(self._tasks), timeout=timeout)