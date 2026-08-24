# Model gotchas

See `_README.md` for the general shape of a model. This file is the short list
of things that have actually broken, each of which passes review and fails
later — at `alembic check` time, or on a user delete in production.

## Datetimes are naive UTC

`Base` stores timestamps as `TIMESTAMP WITHOUT TIME ZONE` and the application
treats every datetime as UTC. New datetime columns must match:

```python
# right
expires_at: datetime | None = Field(
    default=None, sa_column=sa.Column(sa.DateTime, nullable=True)
)
# wrong — DB drift, and psycopg rejects the aware value you write into it
sa.Column(sa.DateTime(timezone=True), nullable=True)
```

Stamp them with the naive helper, never a bare aware `now()`:

```python
datetime.now(timezone.utc).replace(tzinfo=None)
```

Mixing the two is a permanent `alembic check` failure (`Detected type change
from TIMESTAMP(timezone=True) to DateTime()`), which gates every PR.

## `ondelete="SET NULL"` on a user FK, in a table that also points at events

Do not. Use `CASCADE`.

Deleting a user cascades to the events they own. Postgres applies that CASCADE
and any `SET NULL` on the same user **within one statement**, and the SET NULL
update re-runs this row's *other* foreign-key check — against an event the
cascade has already removed. The result is a foreign-key violation on an
ordinary user delete, nowhere near the code that caused it.

`event_invitations.invited_by_id` and `event_join_requests.decided_by_id` were
both written as SET NULL and both hit this. Regression coverage lives in
`tests/api/routes/test_event_members.py::TestUserDeletionCascades`.

If a row genuinely must outlive its user, denormalise the display value onto
the row (as `bookings.cancelled_shift_title` does) rather than reaching for
SET NULL.

## Denormalised `is_sandbox` on `tasks`

`tasks.is_sandbox` duplicates `events.is_sandbox` on purpose. `tasks.event_id`
is `ON DELETE SET NULL` and `Event.tasks` has no `delete-orphan` cascade, so a
task can outlive its event with a NULL `event_id` — and a NULL matches no
`IN (...)`, which is the shape of every event-scoped filter in this application.
An orphan produced that way would be visible to everyone and manageable by
nobody. The flag survives the SET NULL and keeps the exclusion in the `WHERE`
clause. See `docs/SANDBOX.md`.

## Unique + indexed renders as one index

`Field(sa_column=sa.Column(..., unique=True, index=True))` produces a single
unique index — not a `UniqueConstraint` plus a separate index. Write the
migration the same way (`op.create_index(..., unique=True)`), or `alembic check`
reports drift forever.

## The migration must mirror the model exactly

`alembic check` runs in CI, so any disagreement between these files and
`app/alembic/versions/` fails the build. After changing a model, run:

```bash
uv run alembic check
```
