"""Code-level registry of all notification types.

This is the single source of truth for notification types.
The seeder upserts these into the database on startup.
"""

from dataclasses import dataclass
from typing import TypedDict


class NotificationTypeDict(TypedDict):
    code: str
    name: str
    description: str
    category: str
    is_admin_only: bool
    default_channels: list[str]
    is_user_configurable: bool


@dataclass(frozen=True)
class NotificationTypeDef:
    code: str
    name: str
    description: str
    category: str
    is_admin_only: bool = False
    default_channels: list[str] | None = None
    is_user_configurable: bool = True

    def to_dict(self) -> NotificationTypeDict:
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "is_admin_only": self.is_admin_only,
            "default_channels": self.default_channels or ["email"],
            "is_user_configurable": self.is_user_configurable,
        }


# ── Booking notifications ─────────────────────────────────────────

BOOKING_CONFIRMED = NotificationTypeDef(
    code="booking.confirmed",
    name="Booking Confirmed",
    description="Notification when your booking is confirmed",
    category="booking",
    default_channels=["email", "push"],
)

BOOKING_CANCELLED_BY_USER = NotificationTypeDef(
    code="booking.cancelled_by_user",
    name="Booking Cancelled",
    description="Notification when you cancel a booking",
    category="booking",
    default_channels=["email"],
)

BOOKING_CANCELLED_BY_ADMIN = NotificationTypeDef(
    code="booking.cancelled_by_admin",
    name="Booking Cancelled by Admin",
    description="Notification when an admin cancels your booking (shift deleted or regenerated)",
    category="booking",
    default_channels=["email", "push"],
)

BOOKING_SHIFT_COBOOKED = NotificationTypeDef(
    code="booking.shift_cobooked",
    name="Shift Co-booked",
    description="Notification when someone else also books a shift you are on",
    category="booking",
    default_channels=["push"],
)

BOOKING_REMINDER = NotificationTypeDef(
    code="booking.reminder",
    name="Booking Reminder",
    description="Reminder before a booked shift starts",
    category="booking",
    default_channels=["push"],
    is_user_configurable=False,
)

# ── Shift notifications ────────────────────────────────────────────

SHIFT_STARTING_SOON_UNFILLED = NotificationTypeDef(
    code="shift.starting_soon_unfilled",
    name="Shift Starting Soon (Unfilled)",
    description="Alert when a shift starts in 30 minutes but still has open spots",
    category="shift",
    is_admin_only=True,
    default_channels=["email", "push"],
)

SHIFT_TIME_CHANGED = NotificationTypeDef(
    code="shift.time_changed",
    name="Shift Time Changed",
    description="Notification when a shift you booked has its time changed",
    category="shift",
    default_channels=["email", "push"],
)

# ── Task notifications ───────────────────────────────────────────

TASK_PUBLISHED = NotificationTypeDef(
    code="task.published",
    name="Task Published",
    description="Notification when a new task is published",
    category="task",
    default_channels=["email"],
)

# ── Task group notifications ─────────────────────────────────────

EVENT_PUBLISHED = NotificationTypeDef(
    code="event.published",
    name="Event Published",
    description="Notification when a new event is published",
    category="event",
    default_channels=["email"],
)

# ── Availability notifications ────────────────────────────────────

AVAILABILITY_REMINDER = NotificationTypeDef(
    code="availability.reminder",
    name="Availability Reminder",
    description="Reminder to submit your availability for a published event",
    category="availability",
    default_channels=["email", "push"],
)

# ── User / admin notifications ────────────────────────────────────

USER_REGISTERED = NotificationTypeDef(
    code="user.registered",
    name="New User Registered",
    description="Alert when a new user signs up and is pending approval",
    category="admin",
    is_admin_only=True,
    default_channels=["email", "push"],
)

USER_APPROVED = NotificationTypeDef(
    code="user.approved",
    name="Account Approved",
    description="Notification when your account is approved by an admin",
    category="user",
    default_channels=["email", "push"],
)

USER_REJECTED = NotificationTypeDef(
    code="user.rejected",
    name="Account Rejected",
    description="Notification when your account is rejected by an admin",
    category="user",
    default_channels=["email"],
)

# ── All types registry ────────────────────────────────────────────

ALL_NOTIFICATION_TYPES: list[NotificationTypeDef] = [
    BOOKING_CONFIRMED,
    BOOKING_CANCELLED_BY_USER,
    BOOKING_CANCELLED_BY_ADMIN,
    BOOKING_SHIFT_COBOOKED,
    BOOKING_REMINDER,
    SHIFT_STARTING_SOON_UNFILLED,
    SHIFT_TIME_CHANGED,
    TASK_PUBLISHED,
    EVENT_PUBLISHED,
    AVAILABILITY_REMINDER,
    USER_REGISTERED,
    USER_APPROVED,
    USER_REJECTED,
]
