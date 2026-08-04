# pyright: reportPrivateUsage=false
"""Tests for the notification feed router.

Focused on the gaps left by ``tests/api/routes/test_notifications.py``:

* the ``GET /notifications/stream`` SSE endpoint and its event generator,
* ``_sse_format``'s exact wire shape,
* ``list_notifications`` pagination / filtering / ordering,
* cross-user isolation across every endpoint in the router.

The SSE endpoint is driven by calling ``notification_stream`` directly and
stepping its ``StreamingResponse.body_iterator``.  It cannot be exercised
through ``async_client``: httpx's ``ASGITransport`` buffers the whole
response body before returning (it awaits ``app(scope, receive, send)`` to
completion), so ``client.stream()`` against a never-ending SSE generator
would hang forever.
"""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import datetime, timedelta
from typing import cast
from unittest.mock import patch

import pytest
from fastapi import Request
from fastapi.responses import StreamingResponse
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.notifications import feed
from app.core.sse import SSEManager
from app.models.notification import Notification
from app.models.user import User

# Fixed base timestamp so `created_at DESC` ordering assertions are
# deterministic (the model default is wall-clock, whose resolution on
# Windows is coarse enough that rows created in a loop can collide).
_BASE_TIME = datetime(2026, 1, 1, 12, 0, 0)


# ── helpers ───────────────────────────────────────────────────────


async def _make_notification(
    db_session: AsyncSession,
    user_id: uuid.UUID,
    *,
    title: str = "Feed notification",
    type_code: str = "test.feed",
    created_at: datetime = _BASE_TIME,
    is_read: bool = False,
    data: dict[str, str | int | None] | None = None,
    channels_sent: list[str] | None = None,
    channels_failed: list[str] | None = None,
) -> Notification:
    """Insert a notification with an explicit ``created_at``."""
    notif = Notification(
        recipient_id=user_id,
        notification_type_code=type_code,
        title=title,
        body=f"body of {title}",
        is_read=is_read,
        data=data,
        channels_sent=channels_sent or [],
        channels_failed=channels_failed or [],
        created_at=created_at,
    )
    db_session.add(notif)
    await db_session.flush()
    await db_session.refresh(notif)
    return notif


class _StubRequest:
    """Minimal stand-in for Starlette's ``Request``.

    ``notification_stream``'s generator only ever calls ``is_disconnected()``.
    """

    def __init__(self) -> None:
        self.disconnected = False

    async def is_disconnected(self) -> bool:
        return self.disconnected


@asynccontextmanager
async def _bound_session(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    yield session


class _StubSessionMaker:
    """Stand-in for ``app.core.db.async_session`` bound to the test session.

    The SSE endpoint opens its own short-lived session for the initial
    unread count; without this it would talk to the real (non-test) engine
    and never see rows written by the ``db_session`` fixture.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def begin(self) -> AbstractAsyncContextManager[AsyncSession]:
        return _bound_session(self._session)


def _body(response: StreamingResponse) -> AsyncGenerator[str, None]:
    return cast(AsyncGenerator[str, None], response.body_iterator)


@asynccontextmanager
async def _sse_stream(
    db_session: AsyncSession,
    user: User,
    manager: SSEManager,
    request: _StubRequest,
    heartbeat: float = 30.0,
) -> AsyncGenerator[StreamingResponse, None]:
    """Open the SSE endpoint against a throwaway ``SSEManager``.

    The module singleton is never mutated, so no connection or shutdown
    state leaks into other tests.
    """
    with (
        patch.object(feed, "async_session", _StubSessionMaker(db_session)),
        patch.object(feed, "sse_manager", manager),
        patch.object(feed, "SSE_HEARTBEAT_SECONDS", heartbeat),
    ):
        response = await feed.notification_stream(
            request=cast(Request, request), user=user
        )
        try:
            yield response
        finally:
            # Runs the generator's `finally`, which must call disconnect().
            await _body(response).aclose()


# ── _sse_format ───────────────────────────────────────────────────


class TestSseFormat:
    """Wire format of the server-sent event frames."""

    def test_exact_wire_shape(self) -> None:
        """Frames are `event: <name>\\ndata: <json>\\n\\n`."""
        assert (
            feed._sse_format("unread_count", {"unread_count": 3})
            == 'event: unread_count\ndata: {"unread_count": 3}\n\n'
        )

    def test_payload_is_json_encoded(self) -> None:
        """Nested/non-scalar payloads survive as JSON."""
        frame = feed._sse_format("notification", {"id": "abc", "nested": {"n": 1}})

        assert frame.startswith("event: notification\ndata: ")
        assert frame.endswith("\n\n")
        assert json.loads(frame.split("data: ", 1)[1].strip()) == {
            "id": "abc",
            "nested": {"n": 1},
        }


# ── /stream ───────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestNotificationStream:
    """Test suite for GET /notifications/stream (SSE)."""

    async def test_sends_initial_unread_count_and_sse_headers(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """The first frame carries the current unread count."""
        await _make_notification(db_session, test_user.id, title="A")
        await _make_notification(db_session, test_user.id, title="B")
        await _make_notification(db_session, test_user.id, title="C", is_read=True)

        manager = SSEManager()
        request = _StubRequest()

        async with _sse_stream(db_session, test_user, manager, request) as response:
            assert response.media_type == "text/event-stream"
            assert response.headers["cache-control"] == "no-cache"
            assert response.headers["connection"] == "keep-alive"
            assert response.headers["x-accel-buffering"] == "no"

            # The client is registered before the generator is consumed.
            assert len(manager._connections[test_user.id]) == 1

            first = await anext(_body(response))
            assert first == 'event: unread_count\ndata: {"unread_count": 2}\n\n'

        assert test_user.id not in manager._connections

    async def test_initial_count_is_zero_without_notifications(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """A user with no notifications still gets an opening frame."""
        manager = SSEManager()

        async with _sse_stream(
            db_session, test_user, manager, _StubRequest()
        ) as response:
            first = await anext(_body(response))

        assert first == 'event: unread_count\ndata: {"unread_count": 0}\n\n'

    async def test_initial_count_ignores_other_users(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_admin_user: User,
    ) -> None:
        """Another user's unread notifications never reach this stream."""
        await _make_notification(db_session, test_admin_user.id, title="Theirs")
        await _make_notification(db_session, test_user.id, title="Mine")

        manager = SSEManager()

        async with _sse_stream(
            db_session, test_user, manager, _StubRequest()
        ) as response:
            first = await anext(_body(response))

        assert first == 'event: unread_count\ndata: {"unread_count": 1}\n\n'

    async def test_delivers_queued_broadcast(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """A broadcast pushed onto the queue is emitted as an SSE frame."""
        manager = SSEManager()

        async with _sse_stream(
            db_session, test_user, manager, _StubRequest(), heartbeat=5.0
        ) as response:
            gen = _body(response)
            await anext(gen)  # initial unread_count

            await manager.broadcast(
                test_user.id, "notification", {"title": "Hello", "unread_count": 1}
            )

            frame = await anext(gen)

        assert frame.startswith("event: notification\ndata: ")
        assert json.loads(frame.split("data: ", 1)[1].strip()) == {
            "title": "Hello",
            "unread_count": 1,
        }

    async def test_delivers_broadcast_triggered_by_mark_read_endpoint(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """PATCH /{id}/read pushes the new unread count to open streams."""
        first_notif = await _make_notification(db_session, test_user.id, title="One")
        await _make_notification(db_session, test_user.id, title="Two")

        manager = SSEManager()

        async with _sse_stream(
            db_session, test_user, manager, _StubRequest(), heartbeat=5.0
        ) as response:
            gen = _body(response)
            assert await anext(gen) == (
                'event: unread_count\ndata: {"unread_count": 2}\n\n'
            )

            r = await async_client.patch(f"/api/v1/notifications/{first_notif.id}/read")
            assert r.status_code == 200

            pushed = await anext(gen)

        assert pushed == 'event: unread_count\ndata: {"unread_count": 1}\n\n'

    async def test_emits_heartbeat_when_idle(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """With nothing queued the generator emits SSE comments."""
        manager = SSEManager()

        async with _sse_stream(
            db_session, test_user, manager, _StubRequest(), heartbeat=0.01
        ) as response:
            gen = _body(response)
            await anext(gen)  # initial unread_count

            # Two in a row: the second proves the pending queue task is
            # reused across heartbeat timeouts rather than re-created.
            assert await anext(gen) == ": heartbeat\n\n"
            assert await anext(gen) == ": heartbeat\n\n"

        # Closing mid-wait must still cancel the outstanding tasks and
        # deregister the client.
        assert test_user.id not in manager._connections

    async def test_heartbeat_message_then_heartbeat_again(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """A message queued after a heartbeat is delivered, and the loop
        keeps running afterwards on a freshly created queue task."""
        manager = SSEManager()

        async with _sse_stream(
            db_session, test_user, manager, _StubRequest(), heartbeat=0.01
        ) as response:
            gen = _body(response)
            await anext(gen)
            assert await anext(gen) == ": heartbeat\n\n"

            await manager.broadcast(test_user.id, "unread_count", {"unread_count": 7})
            frame = await anext(gen)
            assert frame == 'event: unread_count\ndata: {"unread_count": 7}\n\n'

            # Resuming past the message yield retires the consumed queue task;
            # the stream must carry on rather than stall.
            assert await anext(gen) == ": heartbeat\n\n"

        assert test_user.id not in manager._connections

    async def test_stops_when_client_disconnects(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """A disconnected client ends the stream on the next loop pass."""
        manager = SSEManager()
        request = _StubRequest()

        async with _sse_stream(db_session, test_user, manager, request) as response:
            gen = _body(response)
            await anext(gen)

            request.disconnected = True
            with pytest.raises(StopAsyncIteration):
                await anext(gen)

        assert test_user.id not in manager._connections

    async def test_stops_when_shutdown_already_signalled(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """The loop is skipped entirely once shutdown is set."""
        manager = SSEManager()

        async with _sse_stream(
            db_session, test_user, manager, _StubRequest()
        ) as response:
            gen = _body(response)
            await anext(gen)

            await manager.shutdown()
            with pytest.raises(StopAsyncIteration):
                await anext(gen)

        assert manager.shutdown_event.is_set()
        assert test_user.id not in manager._connections

    async def test_stops_when_shutdown_fires_while_waiting(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Shutdown signalled mid-wait wins the race against the queue."""
        manager = SSEManager()

        async def _signal_shutdown() -> None:
            await asyncio.sleep(0.02)
            await manager.shutdown()

        signaller = asyncio.create_task(_signal_shutdown())
        try:
            async with _sse_stream(
                db_session, test_user, manager, _StubRequest(), heartbeat=5.0
            ) as response:
                gen = _body(response)
                await anext(gen)

                with pytest.raises(StopAsyncIteration):
                    await anext(gen)
        finally:
            await signaller

        assert test_user.id not in manager._connections

    async def test_cancellation_ends_the_stream_cleanly(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """A CancelledError inside the loop breaks out, not bubbles up."""
        manager = SSEManager()

        async with _sse_stream(
            db_session, test_user, manager, _StubRequest(), heartbeat=0.01
        ) as response:
            gen = _body(response)
            await anext(gen)
            # Suspend inside the loop's try/except block.
            assert await anext(gen) == ": heartbeat\n\n"

            with pytest.raises(StopAsyncIteration):
                await gen.athrow(asyncio.CancelledError())

        assert test_user.id not in manager._connections

    async def test_concurrent_streams_are_tracked_independently(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Two streams for one user get separate queues; both get broadcasts."""
        manager = SSEManager()

        async with (
            _sse_stream(
                db_session, test_user, manager, _StubRequest(), heartbeat=5.0
            ) as first,
            _sse_stream(
                db_session, test_user, manager, _StubRequest(), heartbeat=5.0
            ) as second,
        ):
            assert len(manager._connections[test_user.id]) == 2

            await anext(_body(first))
            await anext(_body(second))

            await manager.broadcast(test_user.id, "unread_count", {"unread_count": 4})

            expected = 'event: unread_count\ndata: {"unread_count": 4}\n\n'
            assert await anext(_body(first)) == expected
            assert await anext(_body(second)) == expected

        assert test_user.id not in manager._connections


# ── GET / (list) ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestListNotificationsPaging:
    """Test suite for GET /notifications/ paging, filtering and ordering."""

    async def test_orders_newest_first(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Items come back ordered by created_at descending."""
        for i in range(3):
            await _make_notification(
                db_session,
                test_user.id,
                title=f"N{i}",
                created_at=_BASE_TIME + timedelta(minutes=i),
            )

        r = await async_client.get("/api/v1/notifications/")

        assert r.status_code == 200
        assert [item["title"] for item in r.json()["items"]] == ["N2", "N1", "N0"]

    async def test_skip_and_limit_paginate(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """skip/limit walk the list while total stays the full count."""
        for i in range(5):
            await _make_notification(
                db_session,
                test_user.id,
                title=f"N{i}",
                created_at=_BASE_TIME + timedelta(minutes=i),
            )

        page1 = await async_client.get(
            "/api/v1/notifications/", params={"skip": 0, "limit": 2}
        )
        assert page1.status_code == 200
        body1 = page1.json()
        assert [item["title"] for item in body1["items"]] == ["N4", "N3"]
        assert body1["total"] == 5
        assert body1["unread_count"] == 5
        assert body1["skip"] == 0
        assert body1["limit"] == 2

        page2 = await async_client.get(
            "/api/v1/notifications/", params={"skip": 2, "limit": 2}
        )
        assert [item["title"] for item in page2.json()["items"]] == ["N2", "N1"]
        assert page2.json()["skip"] == 2

        page3 = await async_client.get(
            "/api/v1/notifications/", params={"skip": 4, "limit": 2}
        )
        assert [item["title"] for item in page3.json()["items"]] == ["N0"]
        assert page3.json()["total"] == 5

    async def test_skip_past_the_end_returns_empty_page(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Paging beyond the last item yields no items but a real total."""
        await _make_notification(db_session, test_user.id, title="Only")

        r = await async_client.get("/api/v1/notifications/", params={"skip": 50})

        assert r.status_code == 200
        assert r.json()["items"] == []
        assert r.json()["total"] == 1
        assert r.json()["unread_count"] == 1

    async def test_unread_only_filters_total_but_not_unread_count(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """`total` follows the filter; `unread_count` is always the badge."""
        await _make_notification(db_session, test_user.id, title="Read", is_read=True)
        await _make_notification(db_session, test_user.id, title="Fresh A")
        await _make_notification(db_session, test_user.id, title="Fresh B")

        unfiltered = await async_client.get("/api/v1/notifications/")
        assert unfiltered.json()["total"] == 3
        assert unfiltered.json()["unread_count"] == 2

        filtered = await async_client.get(
            "/api/v1/notifications/", params={"unread_only": True}
        )
        assert filtered.status_code == 200
        body = filtered.json()
        assert body["total"] == 2
        assert body["unread_count"] == 2
        assert {item["title"] for item in body["items"]} == {"Fresh A", "Fresh B"}
        assert all(item["is_read"] is False for item in body["items"])

    async def test_unread_only_respects_paging(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """unread_only combines with skip/limit."""
        await _make_notification(
            db_session,
            test_user.id,
            title="Read",
            is_read=True,
            created_at=_BASE_TIME + timedelta(minutes=9),
        )
        for i in range(3):
            await _make_notification(
                db_session,
                test_user.id,
                title=f"U{i}",
                created_at=_BASE_TIME + timedelta(minutes=i),
            )

        r = await async_client.get(
            "/api/v1/notifications/",
            params={"unread_only": True, "skip": 1, "limit": 1},
        )

        assert r.status_code == 200
        assert [item["title"] for item in r.json()["items"]] == ["U1"]
        assert r.json()["total"] == 3

    async def test_serialises_full_notification_payload(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Every NotificationRead field is populated from the row."""
        notif = await _make_notification(
            db_session,
            test_user.id,
            title="Booking confirmed",
            type_code="booking.confirmed",
            data={"slot_id": "s-1", "count": 2, "missing": None},
            channels_sent=["email", "push"],
            channels_failed=["telegram"],
        )

        r = await async_client.get("/api/v1/notifications/")

        assert r.status_code == 200
        item = r.json()["items"][0]
        assert item["id"] == str(notif.id)
        assert item["recipient_id"] == str(test_user.id)
        assert item["notification_type_code"] == "booking.confirmed"
        assert item["classification"] == "change"
        assert item["title"] == "Booking confirmed"
        assert item["body"] == "body of Booking confirmed"
        assert item["data"] == {"slot_id": "s-1", "count": 2, "missing": None}
        assert item["is_read"] is False
        assert item["read_at"] is None
        assert item["channels_sent"] == ["email", "push"]
        assert item["channels_failed"] == ["telegram"]
        assert item["created_at"] is not None

    async def test_unknown_type_code_falls_back_to_announcement(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Retired/unknown type codes still serialise."""
        await _make_notification(
            db_session, test_user.id, type_code="totally.retired.code"
        )

        r = await async_client.get("/api/v1/notifications/")

        assert r.json()["items"][0]["classification"] == "announcement"

    @pytest.mark.parametrize(
        "params",
        [
            {"skip": -1},
            {"limit": 0},
            {"limit": 201},
        ],
    )
    async def test_rejects_out_of_range_paging(
        self,
        async_client: AsyncClient,
        params: dict[str, int],
    ) -> None:
        """skip >= 0 and 1 <= limit <= 200 are enforced by FastAPI."""
        r = await async_client.get("/api/v1/notifications/", params=params)
        assert r.status_code == 422


# ── cross-user isolation ──────────────────────────────────────────


@pytest.mark.asyncio
class TestNotificationFeedIsolation:
    """A user must never observe or mutate another user's notifications."""

    async def test_list_excludes_other_users_notifications(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_admin_user: User,
    ) -> None:
        """Only the caller's rows are listed."""
        mine = await _make_notification(db_session, test_user.id, title="Mine")
        await _make_notification(db_session, test_admin_user.id, title="Theirs A")
        await _make_notification(db_session, test_admin_user.id, title="Theirs B")

        r = await async_client.get("/api/v1/notifications/")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["unread_count"] == 1
        assert [item["id"] for item in body["items"]] == [str(mine.id)]

    async def test_unread_count_is_per_user(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_admin_user: User,
    ) -> None:
        """The badge count ignores other recipients."""
        for i in range(3):
            await _make_notification(
                db_session, test_admin_user.id, title=f"Theirs {i}"
            )
        await _make_notification(db_session, test_user.id, title="Mine")

        r = await async_client.get("/api/v1/notifications/unread-count")

        assert r.status_code == 200
        assert r.json()["unread_count"] == 1

    async def test_cannot_mark_another_users_notification_read(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_admin_user: User,
    ) -> None:
        """A foreign notification id is indistinguishable from a missing one."""
        foreign = await _make_notification(
            db_session, test_admin_user.id, title="Theirs"
        )

        r = await async_client.patch(f"/api/v1/notifications/{foreign.id}/read")

        assert r.status_code == 404
        await db_session.refresh(foreign)
        assert foreign.is_read is False

    async def test_dismiss_foreign_notification_is_forbidden_and_row_survives(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_admin_user: User,
    ) -> None:
        """A 403 must not delete the row as a side effect."""
        foreign = await _make_notification(
            db_session, test_admin_user.id, title="Theirs"
        )

        r = await async_client.delete(f"/api/v1/notifications/{foreign.id}")

        assert r.status_code == 403
        assert await db_session.get(Notification, foreign.id) is not None

    async def test_mark_all_read_leaves_other_users_untouched(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_admin_user: User,
    ) -> None:
        """mark-all-read is scoped to the caller."""
        await _make_notification(db_session, test_user.id, title="Mine A")
        await _make_notification(db_session, test_user.id, title="Mine B")
        foreign = await _make_notification(
            db_session, test_admin_user.id, title="Theirs"
        )

        r = await async_client.post("/api/v1/notifications/mark-all-read")

        assert r.status_code == 200
        assert r.json()["marked_count"] == 2
        await db_session.refresh(foreign)
        assert foreign.is_read is False

    async def test_dismiss_all_leaves_other_users_untouched(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_admin_user: User,
    ) -> None:
        """dismiss-all only deletes the caller's rows."""
        await _make_notification(db_session, test_user.id, title="Mine A")
        await _make_notification(db_session, test_user.id, title="Mine B")
        foreign = await _make_notification(
            db_session, test_admin_user.id, title="Theirs"
        )

        r = await async_client.post("/api/v1/notifications/dismiss-all")

        assert r.status_code == 200
        assert r.json()["dismissed_count"] == 2
        assert await db_session.get(Notification, foreign.id) is not None

    async def test_dismiss_all_with_nothing_to_dismiss(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_admin_user: User,
    ) -> None:
        """dismiss-all is a no-op when the caller owns nothing."""
        await _make_notification(db_session, test_admin_user.id, title="Theirs")

        r = await async_client.post("/api/v1/notifications/dismiss-all")

        assert r.status_code == 200
        assert r.json()["dismissed_count"] == 0


# ── single-notification mutations ─────────────────────────────────


@pytest.mark.asyncio
class TestMarkAndDismiss:
    """Edge cases around the per-notification endpoints."""

    async def test_mark_read_is_idempotent(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Re-marking a read notification keeps the original read_at."""
        notif = await _make_notification(db_session, test_user.id)

        first = await async_client.patch(f"/api/v1/notifications/{notif.id}/read")
        assert first.status_code == 200
        read_at = first.json()["read_at"]
        assert read_at is not None

        second = await async_client.patch(f"/api/v1/notifications/{notif.id}/read")
        assert second.status_code == 200
        assert second.json()["is_read"] is True
        assert second.json()["read_at"] == read_at

    async def test_mark_read_drops_the_unread_count(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """The badge count reflects the mutation immediately."""
        notif = await _make_notification(db_session, test_user.id, title="A")
        await _make_notification(db_session, test_user.id, title="B")

        before = await async_client.get("/api/v1/notifications/unread-count")
        assert before.json()["unread_count"] == 2

        await async_client.patch(f"/api/v1/notifications/{notif.id}/read")

        after = await async_client.get("/api/v1/notifications/unread-count")
        assert after.json()["unread_count"] == 1

    async def test_dismiss_removes_the_row(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """A dismissed notification disappears from the list."""
        notif = await _make_notification(db_session, test_user.id)

        r = await async_client.delete(f"/api/v1/notifications/{notif.id}")
        assert r.status_code == 204

        listing = await async_client.get("/api/v1/notifications/")
        assert listing.json()["total"] == 0

    async def test_mark_all_read_ignores_already_read(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Only unread rows are counted as newly marked."""
        await _make_notification(db_session, test_user.id, title="Old", is_read=True)
        await _make_notification(db_session, test_user.id, title="New")

        r = await async_client.post("/api/v1/notifications/mark-all-read")

        assert r.status_code == 200
        assert r.json()["marked_count"] == 1

        after = await async_client.get("/api/v1/notifications/unread-count")
        assert after.json()["unread_count"] == 0
