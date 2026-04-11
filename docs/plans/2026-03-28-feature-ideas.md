# Feature Ideas — Brainstorm (2026-03-28)

**Status:** Idea collection — not yet prioritized or approved
**Created:** 2026-03-28

**Goal:** Catalog potential features to extend WirkSam beyond its current core of event management, slot booking, notifications, and availability tracking.

---

## High Impact

### 1. Slot Swap / Trade Requests

Volunteers often can't make a shift after booking. Let users request a swap with another volunteer or post their slot to a "swap board" for others to claim.

- New `SwapRequest` model: links original booking, requesting user, optional target user
- States: `open`, `claimed`, `completed`, `expired`
- Admin can moderate or auto-approve
- Notification integration: notify eligible volunteers when a swap is posted
- **Why:** Reduces admin burden and no-shows without forcing cancellation

### 2. Recurring Events

True recurrence engine (weekly service, monthly meeting) that auto-creates events + slots on a schedule. Currently events are one-off even if grouped.

- Recurrence rule on `Event` or `EventGroup` (e.g. RRULE-style: weekly, biweekly, monthly)
- Admin sets a template event with slot config; system generates instances
- Edit options: single instance vs all future instances
- **Why:** Saves admins significant repetitive work for regular volunteer activities

### 4. Automatic Booking Cancellation Notifications

Already partially built (see `TODO.md`). When admins regenerate duty slots and cancel affected bookings, users should be notified automatically.

- Notification infrastructure exists — needs trigger wiring in slot regeneration logic
- Use existing notification preferences and channels (email, push, telegram)
- **Why:** Lowest-effort high-value item; prevents volunteers from showing up to cancelled shifts

---

## Medium Impact

### 5. Waitlist for Full Slots

When a duty slot hits `max_bookings`, let users join a waitlist. Auto-promote when someone cancels.

- New `WaitlistEntry` model: `user_id` + `duty_slot_id` + `position` + `created_at`
- Auto-promote first in queue on cancellation, with notification
- User can leave waitlist at any time
- **Why:** Captures demand that's currently lost and improves slot fill rates

### 7. Bulk Booking for Admins

Let admins assign multiple volunteers to slots at once, or assign one volunteer to multiple slots.

- Multi-select UI on slot list and user list
- Batch booking endpoint: `POST /bookings/bulk`
- Conflict detection (already booked, slot full)
- **Why:** Large events with 50+ slots are tedious to staff one-by-one

### 8. Check-in / Attendance Tracking

Mark whether volunteers actually showed up.

- Add `checked_in_at` field to `Booking`
- Admin toggle in event detail view or dedicated check-in view
- Optional: QR code per booking for self-check-in
- Feeds into reporting dashboard (#3)
- **Why:** Provides accountability data and identifies reliability patterns

### 9. User Groups / Teams

Organize volunteers into teams beyond the existing event groups.

- New `Team` model with members (many-to-many with `User`)
- Admins can assign slots to teams, filter by team
- Team-level notifications
- **Why:** Enables structured coordination for specialized roles (sound, welcome, kitchen, etc.)

---

## Nice to Have

### 10. Volunteer Skill / Preference Tags

Let users tag themselves with skills and let admins filter when assigning slots by category.

- Tag model or JSONB array on `User`
- Admin can define available tags
- Filter slots by matching category to user tags
- Suggestion engine: "these users have relevant skills for this slot"
- **Why:** Better volunteer-slot matching, especially for specialized duties

### 11. Comments / Notes on Events

Simple comment thread on events or event groups for coordination.

- New `EventComment` model: `user_id` + `event_id` + `body` + `created_at`
- Flat list (no threading needed)
- Notification on new comment (for watchers or all booked users)
- **Why:** Lightweight coordination without external tools ("bring extra chairs", "parking is limited")

### 12. Dark Mode

Tailwind v4 and shadcn-vue both support dark mode well.

- CSS variable toggle in `index.css`
- User preference stored in profile (light / dark / system)
- **Why:** Low effort, high user satisfaction, good accessibility

### 13. Mobile PWA Enhancements

Improve the mobile experience with progressive web app features.

- Service worker for offline viewing of upcoming bookings
- Web app manifest for installability
- Push subscriptions already exist — PWA manifest completes the picture
- **Why:** Volunteers primarily check schedules on their phones

### 14. Export & Sharing

Beyond the existing iCal feed: broader export and sharing options.

- CSV/PDF export of event schedules and booking lists
- Shareable public link for event schedules (no login required)
- Print improvements beyond current print views
- **Why:** Useful for coordinators who need to share schedules with non-users

---

## Recommended Priority

Based on effort-to-value ratio and existing infrastructure:

| Priority | Feature                               | Reason                                  |
| -------- | ------------------------------------- | --------------------------------------- |
| 1        | #4 Booking cancellation notifications | Already partially built, minimal effort |
| 2        | #6 Shift reminders                    | Leverages existing notification system  |
| 3        | #1 Slot swap / trade                  | Solves real volunteer pain point        |
| 4        | #5 Waitlist                           | Natural extension of booking system     |
| 5        | #3 Reporting dashboard                | High admin value, data already exists   |

---

## Decision Log

| Date       | Decision                                                            |
| ---------- | ------------------------------------------------------------------- |
| 2026-03-28 | Ideas captured from codebase analysis. Not yet prioritized by team. |
