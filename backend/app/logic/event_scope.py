"""Helpers for scoping queries to the user's selected event."""

import uuid

from app.models.user import User


def get_user_event_scope(user: User) -> uuid.UUID | None:
    """Return the user's selected event id, or None if no scope is set."""
    return user.selected_event_id
