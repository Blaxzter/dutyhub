"""The "check out a test event" demo: mint it, seed it, and take it away again.

Three modules, in the order they run:

* ``service`` — the entry point. Checks the gate and the ceiling, mints the
  guest, calls the seeder, opens a session.
* ``seed`` — builds one event's worth of believable data around *now*, sized so
  that every screen the guided tour visits has something on it.
* ``cleanup`` — the half that keeps the promise. Nothing here is optional: a
  demo that is not purged is a demo that accumulates.

The invariant the rest of the codebase relies on: a sandbox event is visible to
exactly one account, its own guest. Every listing query in ``app.crud`` filters
``is_sandbox`` out, and ``logic.permissions.require_event_visible`` refuses it
to everyone else — the superadmin included, deliberately.
"""
