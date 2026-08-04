# pyright: reportPrivateUsage=false
"""Tests for the in-memory SSE connection manager (app.core.sse).

Every test uses a fresh ``SSEManager()`` from the ``manager`` fixture rather than
the module-level ``sse_manager`` singleton, so no state leaks between tests.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import pytest

from app.core.sse import SSEManager, sse_manager


class _AlwaysFullQueue(asyncio.Queue[dict[str, Any]]):
    """A queue that always signals backpressure on ``put_nowait``."""

    def put_nowait(self, item: dict[str, Any]) -> None:
        raise asyncio.QueueFull


@pytest.fixture
def manager() -> SSEManager:
    """A fresh manager per test — never the module-level singleton."""
    return SSEManager()


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def other_user_id() -> uuid.UUID:
    return uuid.uuid4()


class TestSingletonIsolation:
    def test_module_singleton_exists(self) -> None:
        assert isinstance(sse_manager, SSEManager)

    def test_fixture_is_not_the_singleton(self, manager: SSEManager) -> None:
        assert manager is not sse_manager

    def test_fresh_manager_starts_empty(self, manager: SSEManager) -> None:
        assert manager._connections == {}
        assert not manager.shutdown_event.is_set()


class TestConnect:
    def test_returns_a_queue(self, manager: SSEManager, user_id: uuid.UUID) -> None:
        queue = manager.connect(user_id)
        assert isinstance(queue, asyncio.Queue)
        assert manager._connections[user_id] == {queue}

    def test_two_clients_get_distinct_queues(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        first = manager.connect(user_id)
        second = manager.connect(user_id)

        assert first is not second
        assert manager._connections[user_id] == {first, second}
        assert len(manager._connections[user_id]) == 2

    def test_queues_start_empty(self, manager: SSEManager, user_id: uuid.UUID) -> None:
        queue = manager.connect(user_id)
        assert queue.empty()

    def test_separate_users_get_separate_entries(
        self, manager: SSEManager, user_id: uuid.UUID, other_user_id: uuid.UUID
    ) -> None:
        mine = manager.connect(user_id)
        theirs = manager.connect(other_user_id)

        assert set(manager._connections) == {user_id, other_user_id}
        assert manager._connections[user_id] == {mine}
        assert manager._connections[other_user_id] == {theirs}


@pytest.mark.asyncio
class TestBroadcast:
    async def test_delivers_to_every_queue_for_the_user(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        first = manager.connect(user_id)
        second = manager.connect(user_id)

        await manager.broadcast(user_id, "notification", {"id": 1})

        assert first.get_nowait() == {"event": "notification", "data": {"id": 1}}
        assert second.get_nowait() == {"event": "notification", "data": {"id": 1}}

    async def test_message_shape_wraps_event_and_data(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        queue = manager.connect(user_id)

        payload: dict[str, Any] = {"unread": 3, "title": "hi"}
        await manager.broadcast(user_id, "unread_count", payload)

        message = queue.get_nowait()
        assert message == {"event": "unread_count", "data": payload}
        assert message["data"] is payload

    async def test_does_not_deliver_to_a_different_user(
        self, manager: SSEManager, user_id: uuid.UUID, other_user_id: uuid.UUID
    ) -> None:
        mine = manager.connect(user_id)
        theirs = manager.connect(other_user_id)

        await manager.broadcast(user_id, "notification", {"id": 1})

        assert mine.qsize() == 1
        assert theirs.empty()

    async def test_unknown_user_is_a_noop(self, manager: SSEManager) -> None:
        await manager.broadcast(uuid.uuid4(), "notification", {"id": 1})

    async def test_unknown_user_does_not_create_a_defaultdict_entry(
        self, manager: SSEManager
    ) -> None:
        await manager.broadcast(uuid.uuid4(), "notification", {"id": 1})

        assert manager._connections == {}

    async def test_user_with_emptied_queue_set_is_a_noop(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        """An entry that exists but holds no queues hits the same early return."""
        manager._connections[user_id] = set()

        await manager.broadcast(user_id, "notification", {"id": 1})

        assert manager._connections[user_id] == set()

    async def test_repeated_broadcasts_queue_up_in_order(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        queue = manager.connect(user_id)

        await manager.broadcast(user_id, "first", {"n": 1})
        await manager.broadcast(user_id, "second", {"n": 2})

        assert queue.qsize() == 2
        assert queue.get_nowait() == {"event": "first", "data": {"n": 1}}
        assert queue.get_nowait() == {"event": "second", "data": {"n": 2}}


@pytest.mark.asyncio
class TestBroadcastQueueFull:
    async def test_bounded_full_queue_does_not_raise(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        full: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1)
        full.put_nowait({"event": "filler", "data": {}})
        manager._connections[user_id].add(full)

        await manager.broadcast(user_id, "notification", {"id": 1})

        # Message was dropped, not appended.
        assert full.qsize() == 1
        assert full.get_nowait() == {"event": "filler", "data": {}}

    async def test_queue_full_is_swallowed_and_logged(
        self,
        manager: SSEManager,
        user_id: uuid.UUID,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        manager._connections[user_id].add(_AlwaysFullQueue())

        with caplog.at_level(logging.WARNING, logger="app.core.sse"):
            await manager.broadcast(user_id, "notification", {"id": 1})

        assert any("queue full" in record.message.lower() for record in caplog.records)

    async def test_full_queue_does_not_block_the_other_queues(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        healthy_a = manager.connect(user_id)
        healthy_b = manager.connect(user_id)
        manager._connections[user_id].add(_AlwaysFullQueue())

        await manager.broadcast(user_id, "notification", {"id": 1})

        assert healthy_a.get_nowait() == {"event": "notification", "data": {"id": 1}}
        assert healthy_b.get_nowait() == {"event": "notification", "data": {"id": 1}}

    async def test_full_queue_does_not_affect_other_users(
        self, manager: SSEManager, user_id: uuid.UUID, other_user_id: uuid.UUID
    ) -> None:
        manager._connections[user_id].add(_AlwaysFullQueue())
        theirs = manager.connect(other_user_id)

        await manager.broadcast(user_id, "notification", {"id": 1})
        await manager.broadcast(other_user_id, "notification", {"id": 2})

        assert theirs.get_nowait() == {"event": "notification", "data": {"id": 2}}


class TestDisconnect:
    def test_removes_only_the_given_queue(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        first = manager.connect(user_id)
        second = manager.connect(user_id)

        manager.disconnect(user_id, first)

        assert manager._connections[user_id] == {second}

    def test_deletes_the_user_entry_once_the_last_queue_goes(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        first = manager.connect(user_id)
        second = manager.connect(user_id)

        manager.disconnect(user_id, first)
        assert user_id in manager._connections

        manager.disconnect(user_id, second)
        assert user_id not in manager._connections
        assert manager._connections == {}

    def test_single_client_disconnect_clears_the_entry(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        queue = manager.connect(user_id)

        manager.disconnect(user_id, queue)

        assert manager._connections == {}

    def test_unknown_user_does_not_raise_and_leaves_dict_empty(
        self, manager: SSEManager
    ) -> None:
        """``_connections`` is a defaultdict: the lookup creates an entry, but the
        empty-set check immediately deletes it again, so the net effect is empty."""
        manager.disconnect(uuid.uuid4(), asyncio.Queue())

        assert manager._connections == {}

    def test_unknown_user_leaves_other_users_untouched(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        queue = manager.connect(user_id)

        manager.disconnect(uuid.uuid4(), asyncio.Queue())

        assert manager._connections == {user_id: {queue}}

    def test_unregistered_queue_for_a_known_user_is_a_noop(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        registered = manager.connect(user_id)
        stranger: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        manager.disconnect(user_id, stranger)

        assert manager._connections[user_id] == {registered}

    def test_double_disconnect_is_idempotent(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        queue = manager.connect(user_id)

        manager.disconnect(user_id, queue)
        manager.disconnect(user_id, queue)

        assert manager._connections == {}

    def test_disconnect_only_affects_the_named_user(
        self, manager: SSEManager, user_id: uuid.UUID, other_user_id: uuid.UUID
    ) -> None:
        mine = manager.connect(user_id)
        theirs = manager.connect(other_user_id)

        manager.disconnect(user_id, mine)

        assert manager._connections == {other_user_id: {theirs}}


@pytest.mark.asyncio
class TestShutdown:
    async def test_shutdown_sets_the_event(self, manager: SSEManager) -> None:
        assert not manager.shutdown_event.is_set()

        await manager.shutdown()

        assert manager.shutdown_event.is_set()

    async def test_shutdown_is_idempotent(self, manager: SSEManager) -> None:
        await manager.shutdown()
        await manager.shutdown()

        assert manager.shutdown_event.is_set()

    async def test_shutdown_does_not_drop_connections(
        self, manager: SSEManager, user_id: uuid.UUID
    ) -> None:
        queue = manager.connect(user_id)

        await manager.shutdown()

        assert manager._connections == {user_id: {queue}}

    async def test_awaiting_the_event_returns_after_shutdown(
        self, manager: SSEManager
    ) -> None:
        await manager.shutdown()

        assert await asyncio.wait_for(manager.shutdown_event.wait(), timeout=1) is True


class TestShutdownEventProperty:
    def test_returns_an_asyncio_event(self, manager: SSEManager) -> None:
        assert isinstance(manager.shutdown_event, asyncio.Event)

    def test_returns_the_same_instance_every_time(self, manager: SSEManager) -> None:
        assert manager.shutdown_event is manager.shutdown_event
        assert manager.shutdown_event is manager._shutdown_event

    def test_each_manager_has_its_own_event(self, manager: SSEManager) -> None:
        other = SSEManager()
        assert manager.shutdown_event is not other.shutdown_event
