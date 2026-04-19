"""
SQLModel imports and base classes for the application.

This module provides the base SQLModel class and imports for database models.
"""

from sqlmodel import SQLModel

from .base import Base  # Import the Base model for common fields and functionality
from .booking import Booking
from .booking_reminder import BookingReminder
from .calendar_feed import CalendarFeedToken
from .event import Event
from .event_manager import EventManager
from .notification import (
    Notification,
    NotificationSubscription,
    NotificationType,
    PushSubscription,
    TelegramBinding,
)
from .shift import Shift
from .shift_batch import ShiftBatch
from .site_settings import SiteSettings
from .task import Task
from .user import User
from .user_availability import UserAvailability, UserAvailabilityDate

__all__ = [
    "SQLModel",
    "Base",
    "Booking",
    "BookingReminder",
    "CalendarFeedToken",
    "Shift",
    "Task",
    "Event",
    "EventManager",
    "Notification",
    "NotificationSubscription",
    "NotificationType",
    "PushSubscription",
    "SiteSettings",
    "ShiftBatch",
    "TelegramBinding",
    "User",
    "UserAvailability",
    "UserAvailabilityDate",
]
