# E2E gotchas

`README.md` covers how to run these. This is the short list of things that
waste an afternoon.

## Run it locally, isolated — no Auth0 needed

Default mode (`USE_AUTH0_E2E` unset) seeds users straight into the DB and
bypasses Auth0. It needs the backend running with `TESTING=true`; Playwright
starts the frontend itself.

```bash
docker compose up db -d                                   # note: no -f
cd backend && TESTING=true ENVIRONMENT=local uv run uvicorn app.main:app --port 8787
cd frontend && pnpm exec playwright test --reporter=list  # list, or it opens a server and blocks
```

Filter noisy Vite output with `| grep -vE "^\[WebServer\]"`.

## Membership is required for almost everything

Authorisation lives on the event, so a seeded user who is not a member of
anything sees an empty app and cannot even set a selected event. Fixtures put
people into events through the real invitation endpoints:

- `joinEvent(eventId, inviterEmail, inviteeEmail, role)` in `fixtures.ts`
- `addMember(inviterPage, inviteePage, eventId, email, role)` in `helpers/api.ts`

Both take *two* identities on purpose — an invitation is created by an
organiser and redeemed by the invitee. There is deliberately no "add this user"
endpoint to shortcut.

Pass `disposableUserOptions: { joinWorkerEvent: false }` for a user in no event
at all, which is what a genuine first sign-in looks like.

## Assertions must survive parallel workers

Every worker seeds its **own** admin, member and event, and they all run
against one database. So a locator that is unique within your test can match
several elements once other workers are doing the same thing.

```ts
// flaky — other workers feature their own events concurrently
await expect(page.locator('[data-featured="true"]')).toContainText(name)
// stable — pin it to this worker's fixture
await expect(
  page.locator('[data-featured="true"]').filter({ hasText: workerEvent.name }),
).toHaveCount(1)
```

Never target `adminUser` / `memberUser` / `workerEvent` with a destructive
action — they are shared by every test that worker runs. Use the `disposable*`
fixtures, which are deleted in teardown.

## Asserting a refusal

`api()` throws on any non-2xx, which loses the status. Use `apiStatus()` when
the test cares *which* refusal it got — 403 ("not allowed here") and 404 ("you
cannot even see this") mean different things in this codebase and are worth
distinguishing.

## Don't touch the shared fixtures, including indirectly

`adminUser`, `memberUser` and `workerEvent` are shared by every test a worker
runs, so anything that mutates them poisons whatever comes later — and the
failure surfaces somewhere else entirely, which makes it look like flakiness.

The subtle case is mutation through the UI. Accepting an invitation on
`/invite/:token` calls `setSelectedEvent()`, so clicking that button as
`memberPage` repoints the shared member at a throwaway event. When the test
tears that event down, the FK nulls the selection, and every later test that
needs a selected event gets bounced to the picker instead of the page it was
testing.

Any test that *acts* as an invitee — accepting, joining, switching events —
should use `disposablePage` / `disposableUser`, which are deleted in teardown.
Read-only checks (viewing an invite, asserting a refusal) are fine as
`memberPage`.

Before blaming flakiness, reproduce serially — that is how CI runs each shard:

```bash
pnpm exec playwright test --workers=1
```

If it fails there, it is not flaky. It is an ordering bug, and the cause is
usually shared state.
