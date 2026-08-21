"""Helpers for scoping queries to the events a user may see."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.event_membership import event_membership as crud_membership
from app.models.user import User


def get_user_event_scope(user: User) -> uuid.UUID | None:
    """Return the user's selected event id, or None if no scope is set."""
    return user.selected_event_id


async def get_visible_event_ids(
    session: AsyncSession,
    user: User,
) -> list[uuid.UUID] | None:
    """Events whose contents this user may see, or None for no restriction.

    Returns None only for the platform superadmin. Everyone else gets the
    explicit list of events they are a member of — which may be empty, and an
    empty list is a real answer meaning "nothing", not "everything". Callers
    must keep that distinction: collapsing ``[]`` to ``None`` would hand a
    brand-new account the whole database.
    """
    if user.is_admin:
        return None
    return await crud_membership.list_event_ids_for_user(session, user_id=user.id)


async def get_manageable_event_ids(
    session: AsyncSession,
    user: User,
) -> list[uuid.UUID] | None:
    """Events this user may manage, or None for no restriction (superadmin)."""
    if user.is_admin:
        return None
    return await crud_membership.list_event_ids_for_user(
        session, user_id=user.id, minimum_role="admin"
    )
