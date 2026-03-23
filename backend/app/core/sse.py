"""In-memory SSE connection manager for real-time notification updates."""

import asyncio
import uuid
from collections import defaultdict
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class SSEManager:
    """Manages per-user SSE connections via asyncio queues.

    Each connected client gets its own queue. When a notification event
    occurs, the relevant user's queues all receive the update.
    """

    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, set[asyncio.Queue[dict[str, Any]]]] = (
            defaultdict(set)
        )
        self._shutdown_event = asyncio.Event()

    def connect(self, user_id: uuid.UUID) -> asyncio.Queue[dict[str, Any]]:
        """Register a new SSE client for a user. Returns the queue to read from."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._connections[user_id].add(queue)
        logger.debug(
            f"SSE connect: user={user_id}, total={len(self._connections[user_id])}"
        )
        return queue

    def disconnect(
        self, user_id: uuid.UUID, queue: asyncio.Queue[dict[str, Any]]
    ) -> None:
        """Unregister an SSE client."""
        self._connections[user_id].discard(queue)
        if not self._connections[user_id]:
            del self._connections[user_id]
        logger.debug(f"SSE disconnect: user={user_id}")

    @property
    def shutdown_event(self) -> asyncio.Event:
        return self._shutdown_event

    async def shutdown(self) -> None:
        """Signal all SSE connections to close (called during app shutdown)."""
        self._shutdown_event.set()
        logger.info("SSE shutdown signalled, closing all connections")

    async def broadcast(
        self, user_id: uuid.UUID, event: str, data: dict[str, Any]
    ) -> None:
        """Push an event to all SSE connections for a given user."""
        queues = self._connections.get(user_id)
        if not queues:
            return
        message = {"event": event, "data": data}
        for queue in queues:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning(f"SSE queue full for user={user_id}, dropping message")


sse_manager = SSEManager()
