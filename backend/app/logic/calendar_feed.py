"""Generate iCalendar (.ics) feeds from user bookings."""

import datetime as dt
from collections.abc import Sequence

from icalendar import Alarm, Calendar, Event  # type: ignore[import-untyped]

from app.models.booking import Booking


def build_calendar(
    bookings: Sequence[Booking],
    reminder_offsets: Sequence[int] | None = None,
) -> bytes:
    """Convert confirmed bookings into an iCalendar byte string.

    Each booking with a linked duty_slot becomes a VEVENT.
    Slots without times become all-day events.
    """
    cal = Calendar()
    cal.add("prodid", "-//WirkSam//Duty Bookings//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", "WirkSam Bookings")

    for booking in bookings:
        if booking.status != "confirmed":
            continue

        slot = booking.duty_slot
        if slot is None:
            continue

        event = Event()
        event.add("uid", f"booking-{booking.id}@wirksam")

        # Build summary: "Event Name: Slot Title" or just "Slot Title"
        event_name = getattr(slot, "event", None) and slot.event.name
        summary = f"{event_name}: {slot.title}" if event_name else slot.title
        event.add("summary", summary)

        # Date/time handling
        if slot.start_time is not None:
            dtstart = dt.datetime.combine(slot.date, slot.start_time)
            event.add("dtstart", dtstart)
            if slot.end_time is not None:
                dtend = dt.datetime.combine(slot.date, slot.end_time)
                event.add("dtend", dtend)
            else:
                # Default 1-hour duration when only start time is set
                event.add("dtend", dtstart + dt.timedelta(hours=1))
        else:
            # All-day event (DATE value type)
            event.add("dtstart", slot.date)
            event.add("dtend", slot.date + dt.timedelta(days=1))

        if slot.location:
            event.add("location", slot.location)

        # Description
        desc_parts: list[str] = []
        if event_name:
            desc_parts.append(event_name)
        if slot.category:
            desc_parts.append(slot.category)
        if booking.notes:
            desc_parts.append(booking.notes)
        desc_parts.append("Booked via WirkSam")
        event.add("description", "\n".join(desc_parts))

        event.add("status", "CONFIRMED")
        event.add("dtstamp", booking.created_at or dt.datetime.now(dt.timezone.utc))
        if booking.updated_at:
            event.add("last-modified", booking.updated_at)

        # Reminders from user's default offsets (or 1-hour fallback)
        offsets = reminder_offsets if reminder_offsets else [60]
        for offset in offsets:
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", summary)
            alarm.add("trigger", dt.timedelta(minutes=-offset))
            event.add_component(alarm)

        cal.add_component(event)

    return cal.to_ical()
