"""Notification trigger helpers called from route handlers via BackgroundTasks.

Each function opens its own DB session since BackgroundTasks run after
the request session is closed.
"""

import datetime as dt
import uuid

from app.core.db import async_session
from app.core.logger import get_logger
from app.logic.notifications.messages import get_message
from app.logic.notifications.service import NotificationService

logger = get_logger(__name__)


async def dispatch_booking_confirmed(
    *,
    booking_id: uuid.UUID,
    user_id: uuid.UUID,
    slot_title: str,
    slot_date: dt.date | None = None,
    slot_start_time: dt.time | None = None,
    slot_end_time: dt.time | None = None,
    slot_location: str | None = None,
    task_name: str | None = None,
    slot_id: uuid.UUID,
    task_id: uuid.UUID,
    event_id: uuid.UUID | None = None,
) -> None:
    """Notify user that their booking was confirmed."""
    try:
        async with async_session() as db:
            svc = NotificationService(db)
            scope_chain = _build_scope_chain(slot_id, task_id, event_id)

            def _factory(lang: str) -> tuple[str, str]:
                return get_message(
                    "booking.confirmed",
                    lang,
                    slot_title=slot_title,
                    task_name=task_name or "",
                    date=slot_date.strftime("%d.%m.%Y") if slot_date else "",
                    start_time=slot_start_time.strftime("%H:%M")
                    if slot_start_time
                    else "",
                    end_time=slot_end_time.strftime("%H:%M") if slot_end_time else "",
                    location=slot_location or "",
                )

            await svc.notify(
                recipient_ids=[user_id],
                type_code="booking.confirmed",
                message_factory=_factory,
                data={
                    "booking_id": str(booking_id),
                    "slot_id": str(slot_id),
                    "task_id": str(task_id),
                },
                scope_chain=scope_chain,
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to dispatch booking.confirmed notification")


async def dispatch_booking_cobooked(
    *,
    slot_id: uuid.UUID,
    slot_title: str,
    task_id: uuid.UUID,
    event_id: uuid.UUID | None = None,
    new_user_name: str | None,
    existing_user_ids: list[uuid.UUID],
) -> None:
    """Notify existing bookers that someone else also booked their slot."""
    if not existing_user_ids:
        return
    try:
        async with async_session() as db:
            svc = NotificationService(db)
            scope_chain = _build_scope_chain(slot_id, task_id, event_id)
            name = new_user_name or "Someone"
            await svc.notify(
                recipient_ids=existing_user_ids,
                type_code="booking.slot_cobooked",
                message_factory=lambda lang, _name=name: get_message(
                    "booking.slot_cobooked", lang, name=_name, slot_title=slot_title
                ),
                data={
                    "slot_id": str(slot_id),
                    "task_id": str(task_id),
                },
                scope_chain=scope_chain,
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to dispatch booking.slot_cobooked notification")


async def dispatch_booking_cancelled_by_user(
    *,
    booking_id: uuid.UUID,
    user_id: uuid.UUID,
    slot_title: str,
    slot_id: uuid.UUID,
    task_id: uuid.UUID,
    event_id: uuid.UUID | None = None,
) -> None:
    """Notify user that their booking cancellation was processed."""
    try:
        async with async_session() as db:
            svc = NotificationService(db)
            scope_chain = _build_scope_chain(slot_id, task_id, event_id)
            await svc.notify(
                recipient_ids=[user_id],
                type_code="booking.cancelled_by_user",
                message_factory=lambda lang: get_message(
                    "booking.cancelled_by_user", lang, slot_title=slot_title
                ),
                data={
                    "booking_id": str(booking_id),
                    "slot_id": str(slot_id),
                    "task_id": str(task_id),
                },
                scope_chain=scope_chain,
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to dispatch booking.cancelled_by_user notification")


async def dispatch_booking_cancelled_by_admin(
    *,
    user_ids: list[uuid.UUID],
    slot_title: str,
    task_name: str | None = None,
    task_id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> None:
    """Notify users that their bookings were cancelled by admin action."""
    if not user_ids:
        return
    try:
        async with async_session() as db:
            svc = NotificationService(db)

            def _factory(lang: str) -> tuple[str, str]:
                if lang == "de":
                    task_label = f' für das Task „{task_name}"' if task_name else ""
                    detail = f" (Grund: {reason})" if reason else ""
                else:
                    task_label = f' for task "{task_name}"' if task_name else ""
                    detail = f" (Reason: {reason})" if reason else ""
                return get_message(
                    "booking.cancelled_by_admin",
                    lang,
                    slot_title=slot_title,
                    task_label=task_label,
                    detail=detail,
                )

            await svc.notify(
                recipient_ids=user_ids,
                type_code="booking.cancelled_by_admin",
                message_factory=_factory,
                data={
                    "task_id": str(task_id) if task_id else None,
                    "event_id": str(event_id) if event_id else None,
                },
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to dispatch booking.cancelled_by_admin notification")


async def dispatch_slot_time_changed(
    *,
    slot_id: uuid.UUID,
    slot_title: str,
    task_id: uuid.UUID,
    event_id: uuid.UUID | None = None,
    booked_user_ids: list[uuid.UUID],
) -> None:
    """Notify bookers that a slot's time was changed."""
    if not booked_user_ids:
        return
    try:
        async with async_session() as db:
            svc = NotificationService(db)
            scope_chain = _build_scope_chain(slot_id, task_id, event_id)
            await svc.notify(
                recipient_ids=booked_user_ids,
                type_code="slot.time_changed",
                message_factory=lambda lang: get_message(
                    "slot.time_changed", lang, slot_title=slot_title
                ),
                data={
                    "slot_id": str(slot_id),
                    "task_id": str(task_id),
                },
                scope_chain=scope_chain,
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to dispatch slot.time_changed notification")


async def dispatch_task_published(
    *,
    task_id: uuid.UUID,
    task_name: str,
    event_id: uuid.UUID | None = None,
) -> None:
    """Notify all active users that an task was published."""
    try:
        from sqlalchemy import select
        from sqlmodel import col

        from app.models.user import User

        async with async_session() as db:
            result = await db.execute(
                select(User).where(col(User.is_active) == True)  # noqa: E712
            )
            users = result.scalars().all()
            user_ids = [u.id for u in users]

            if user_ids:
                svc = NotificationService(db)
                scope_chain: list[tuple[str, uuid.UUID]] = [("task", task_id)]
                if event_id:
                    scope_chain.append(("event", event_id))
                await svc.notify(
                    recipient_ids=user_ids,
                    type_code="task.published",
                    message_factory=lambda lang: get_message(
                        "task.published", lang, task_name=task_name
                    ),
                    data={"task_id": str(task_id)},
                    scope_chain=scope_chain,
                )
                await db.commit()
    except Exception:
        logger.exception("Failed to dispatch task.published notification")


async def dispatch_event_published(
    *,
    event_id: uuid.UUID,
    event_name: str,
) -> None:
    """Notify all active users that an task group was published."""
    try:
        from sqlalchemy import select
        from sqlmodel import col

        from app.models.user import User

        async with async_session() as db:
            result = await db.execute(
                select(User).where(col(User.is_active) == True)  # noqa: E712
            )
            users = result.scalars().all()
            user_ids = [u.id for u in users]

            if user_ids:
                svc = NotificationService(db)
                await svc.notify(
                    recipient_ids=user_ids,
                    type_code="event.published",
                    message_factory=lambda lang: get_message(
                        "event.published",
                        lang,
                        event_name=event_name,
                    ),
                    data={"event_id": str(event_id)},
                    scope_chain=[("event", event_id)],
                )
                await db.commit()
    except Exception:
        logger.exception("Failed to dispatch event.published notification")


async def dispatch_user_registered(
    *,
    user_id: uuid.UUID,
    user_name: str | None,
    user_email: str | None,
) -> None:
    """Notify admins that a new user registered."""
    try:
        async with async_session() as db:
            svc = NotificationService(db)
            name = user_name or user_email or "Unknown"
            await svc.notify_admins(
                type_code="user.registered",
                message_factory=lambda lang, _name=name: get_message(
                    "user.registered", lang, name=_name
                ),
                data={"user_id": str(user_id)},
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to dispatch user.registered notification")


async def dispatch_user_approved(
    *,
    user_id: uuid.UUID,
) -> None:
    """Notify user that their account was approved."""
    try:
        async with async_session() as db:
            svc = NotificationService(db)
            await svc.notify(
                recipient_ids=[user_id],
                type_code="user.approved",
                message_factory=lambda lang: get_message("user.approved", lang),
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to dispatch user.approved notification")


async def dispatch_user_rejected(
    *,
    user_id: uuid.UUID,
    reason: str | None = None,
) -> None:
    """Notify user that their account was rejected."""
    try:
        async with async_session() as db:
            svc = NotificationService(db)

            def _factory(lang: str) -> tuple[str, str]:
                if lang == "de":
                    detail = f" Grund: {reason}" if reason else ""
                else:
                    detail = f" Reason: {reason}" if reason else ""
                return get_message("user.rejected", lang, detail=detail)

            await svc.notify(
                recipient_ids=[user_id],
                type_code="user.rejected",
                message_factory=_factory,
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to dispatch user.rejected notification")


def _build_scope_chain(
    slot_id: uuid.UUID | None = None,
    task_id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
) -> list[tuple[str, uuid.UUID]]:
    """Build a scope chain from most specific to least specific."""
    chain: list[tuple[str, uuid.UUID]] = []
    if slot_id:
        chain.append(("duty_slot", slot_id))
    if task_id:
        chain.append(("task", task_id))
    if event_id:
        chain.append(("event", event_id))
    return chain
