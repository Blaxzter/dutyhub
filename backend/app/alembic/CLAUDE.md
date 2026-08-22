# Writing migrations

`alembic check` runs in the *Test Backend* CI job, so a migration that does not
exactly reproduce the models fails the PR. The column-level rules that catch
people out (naive UTC datetimes, `unique=True, index=True` rendering as one
index, why user FKs cascade rather than SET NULL) are in
`app/models/CLAUDE.md` — read that before adding columns here.

## Always verify the round trip

Applying cleanly is not enough; the downgrade has to work too, and `check` has
to be quiet afterwards:

```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
uv run alembic check          # must say "No new upgrade operations detected"
```

While iterating on an *unreleased* migration you will desync your local DB —
the downgrade you are editing no longer matches the upgrade that ran. Reconcile
by hand against the dev database rather than guessing:

```bash
docker exec wirksam-db-1 psql -U admin -d app -c '<the corrective DDL>'
```

## Data migrations

The test database is built by running these migrations (not by
`metadata.create_all`), so backfill SQL is exercised by the whole backend
suite. That makes it worth writing carefully.

- Guard inserts with `ON CONFLICT ON CONSTRAINT <name> DO NOTHING/UPDATE` —
  backfills usually overlap.
- A backfill that grants access must have a terminal fallback. The self-service
  migration promotes `created_by_id` to owner, then the earliest manager, then
  a superadmin, specifically so no event can end up with nobody able to
  administer it.
- Say in the docstring *why* each step exists, in terms of what a user would
  otherwise lose. Someone reading it during an incident needs the intent, not a
  restatement of the SQL.

## Renaming tables

Postgres does not rename the dependent objects for you. `op.rename_table` must
be followed by explicit renames of every index, primary key, unique constraint
and foreign key, or the next migration's `alembic check` reports drift on names
nobody looked at. `20260821_0001_self_service_events.py` renames
`event_managers` → `event_memberships` and is the worked example.
