# Replacing Auth0 with local, database-backed authentication

**Status:** implementation spec — the single source of truth for this migration.
**Date:** 2026-08-23

Auth0 contributes exactly one thing to this codebase: a validated `sub` string.
Everything downstream — `User`, `roles`, `EventMembership`, `require_event_role`,
`require_event_visible`, `event_scope` — is already pure database logic and is
**not** touched by this migration. We are replacing an *issuer*, not an
authorisation model.

---

## 1. Decisions (settled — do not re-litigate)

| # | Decision | Why |
|---|---|---|
| D1 | Access token: **HS256 JWT, 15 min, in-memory on the client**. Refresh token: **opaque, 30 d, httpOnly cookie, rotating, hashed at rest**. | Revocation and reuse-detection, which Auth0 gave for free. |
| D2 | JWT `sub` = **`User.id` (UUID string)**, plus `jti` = auth-session id and `typ` = `"access"`. | No second identity lookup path; `deps` resolves by primary key. |
| D3 | `users.auth0_sub` is **renamed to `users.subject`** (catalog-only rename). The `demo|`, `test|` prefix convention is **kept**; password accounts get `local|<uuid4hex>`. | Leaving `auth0_sub` behind after removing Auth0 guarantees the idiom gets copied into new code. The prefixes are load-bearing (see §7). |
| D4 | Login is **not** blocked on unverified email. Verification is a soft nudge in the UI. | Keeps 317 E2E tests and seeded users working; friendlier. Revisit later if needed. |
| D5 | The `X-Test-User-Email` E2E bypass **stays** (still `settings.TESTING`-gated). Only the *Auth0-specific* half (`fake-auth0.ts`, `@auth0/auth0-vue`) is replaced. | In CI the Playwright browser origin and `VITE_API_URL=http://backend:8787` are genuinely cross-site, so a `SameSite=Lax` refresh cookie is silently dropped and `SameSite=None` needs `Secure` needs HTTPS. Real-login E2E would pass locally and fail in CI. Removing the bypass is a separate, later change. |
| D6 | Email uniqueness via a **partial unique index on `lower(email)` WHERE email IS NOT NULL**; `email` stays nullable. Lookups are case-insensitive. | Existing rows may have NULL emails; registration requires one. |
| D7 | Refresh-token **reuse detection**: presenting an already-revoked token revokes every session of that user. | Standard, cheap, catches theft. |
| D8 | Rate limiting: small **in-process** limiter, disabled under `settings.TESTING`. | No Redis in the stack. Per-worker limits are documented as a known approximation. |
| D9 | `nickname` and `bio` get **real columns**. `POST /users/me` is replaced by `GET /users/me`. | Today they are Auth0-only and faked into the PATCH response by `model_copy`; with Auth0 gone they would write to nothing. |
| D10 | Table is `auth_sessions` (model `AuthSession`), **not** `sessions`. | `session` already means `AsyncSession` in every route signature. |

---

## 2. Data model

### 2.1 `users` (modified) — `backend/app/models/user.py`

- `auth0_sub: str` → **`subject: str`** (same column semantics: `sa.String, unique=True, index=True`).
- **new** `password_hash: str | None` — `sa.Column(sa.String, nullable=True)`. Null = account has no password (demo/test/legacy).
- **new** `nickname: str | None` — `sa.Column(sa.String(50), nullable=True)`.
- **new** `bio: str | None` — `sa.Column(sa.Text, nullable=True)`.

### 2.2 `auth_sessions` (new) — `backend/app/models/auth_session.py`

Inherits `Base` (uuid4 PK, naive-UTC `created_at`/`updated_at`).

| Column | Type | Notes |
|---|---|---|
| `user_id` | `sa.Uuid` FK `users.id` **`ondelete="CASCADE"`**, indexed, not null | never `SET NULL` — see §7 G3 |
| `refresh_token_hash` | `sa.String(64)` unique index, not null | sha256 hex of the opaque token |
| `expires_at` | `sa.DateTime` not null | **naive UTC** |
| `revoked_at` | `sa.DateTime` nullable | |
| `last_used_at` | `sa.DateTime` nullable | |
| `user_agent` | `sa.String(255)` nullable | for the Security settings list |
| `ip_address` | `sa.String(45)` nullable | IPv6-safe width |

### 2.3 `user_tokens` (new) — `backend/app/models/user_token.py`

Modelled on `models/event_invitation.py`. One row per outstanding email-borne token.

| Column | Type | Notes |
|---|---|---|
| `user_id` | `sa.Uuid` FK `users.id` `ondelete="CASCADE"`, indexed, not null | |
| `purpose` | `sa.String(32)` not null | `"verify_email"` or `"reset_password"` |
| `token_hash` | `sa.String(64)` unique index, not null | sha256 hex |
| `expires_at` | `sa.DateTime` not null | naive UTC |
| `consumed_at` | `sa.DateTime` nullable | |

Both new models **must** be registered in `backend/app/models/__init__.py` or Alembic autogenerate will not see them.

### 2.4 Migration — `backend/app/alembic/versions/20260823_0001_local_auth.py`

`down_revision = "20260821_0001"` (current head).

Order inside `upgrade()`:

1. Guard: `SELECT lower(email), count(*) ... HAVING count(*) > 1` — if any rows come back, `raise RuntimeError` naming the duplicates. Fail loudly rather than mangle data. (Empty CI DBs pass trivially.)
2. `op.alter_column("users", "auth0_sub", new_column_name="subject")` then `op.execute("ALTER INDEX ix_users_auth0_sub RENAME TO ix_users_subject")` — **catalog-only**, never drop/create.
3. `op.add_column` x3 (`password_hash`, `nickname`, `bio`), all nullable.
4. `op.execute("CREATE UNIQUE INDEX ix_users_email_lower ON users (lower(email)) WHERE email IS NOT NULL")`.
5. `op.create_table("auth_sessions", ...)` + its three indexes — spell out `id`/`created_at`/`updated_at` by hand; Alembic does not know they come from `Base`.
6. `op.create_table("user_tokens", ...)` + indexes.

`downgrade()` fully reverses all six steps.

Conventions: `import sqlalchemy as sa` then `from alembic import op`; `sa.` types only (no `sqlmodel.sql.sqltypes`); docstring = human sentence, then prose rationale, then `Revision ID:` / `Revises:` / `Create Date:`; section banner comments; real `downgrade()`.

Verify with `uv run --directory backend alembic check` — CI gates on it.

---

## 3. Backend modules

### 3.1 `backend/app/core/security.py` (extend the existing file — do not create a second hashing helper)

```
hash_password(password: str) -> str                        # guard >72 BYTES, raise ValueError
verify_password(plain: str, hashed: str | None) -> bool    # None/empty/malformed -> False, never raise
hash_token(raw: str) -> str                                # sha256 hexdigest, 64 chars
generate_token() -> str                                    # secrets.token_urlsafe(32) — house standard
create_access_token(*, user_id, session_id) -> tuple[str, int]   # (jwt, expires_in_seconds)
decode_access_token(token: str) -> AccessClaims                  # raises AuthTokenError
```

bcrypt 5.0.0 caveats — both are real and must be handled:

- `hashpw`/`checkpw` **raise** `ValueError` on >72 **bytes** (not characters — a German umlaut is 2 bytes). No silent truncation any more.
- `checkpw` **raises** `ValueError: Invalid salt` on a malformed or empty hash. `password_hash` is nullable, so every legacy row would 500 on a login attempt without a try/except.

PyJWT 2.13: always pass `algorithms=["HS256"]`; catch `jwt.ExpiredSignatureError` **before** `jwt.InvalidTokenError` (it subclasses it); do not set `aud` (it would force an `audience=` argument on every decode).

### 3.2 `backend/app/core/rate_limit.py` (new)

In-process fixed-window counter, `asyncio.Lock`-guarded, keyed by `(bucket, identifier)`.
`RateLimiter(limit: int, window_seconds: int)` with `async def check(key: str) -> None` raising via
`raise_problem(429, code="auth.rate_limited", ...)`. **No-op when `settings.TESTING`** — six parallel
Playwright workers would otherwise trip any sane per-IP limit and it would read as flakiness.
Docstring must state the per-worker approximation (`fastapi run --workers 4`).

Buckets: `login` 10/5 min per IP+email, `register` 5/h per IP, `forgot_password` 5/h per IP+email,
`reset_password` 10/h per IP, `resend_verification` 3/h per user.

### 3.3 `backend/app/logic/auth/`

- `passwords.py` — policy (`PASSWORD_MIN_LENGTH`, <=72 bytes), `validate_password_strength`.
- `tokens.py` — mint/rotate/revoke refresh tokens against `auth_sessions`; reuse detection (D7); issue/verify email-borne `user_tokens`.
- `service.py` — the flows, each `async def` taking `session: AsyncSession`. Owns `sync_superadmin_role(user)`, which replaces the duplicated `SUPERADMIN_EMAILS` promotion at `deps.py:109-116` and `routes/users.py:99-106`. **This is the only mechanism that creates the first platform admin — it must survive.**
- `emails.py` — see §5.

### 3.4 `backend/app/schemas/auth.py` (new)

`RegisterRequest` (email `EmailStr`, password, name, preferred_language), `LoginRequest`,
`TokenResponse` (`access_token`, `token_type="bearer"`, `expires_in`, `user: UserProfile`),
`RefreshResponse`, `ForgotPasswordRequest`, `ResetPasswordRequest` (token, password),
`VerifyEmailRequest` (token), `ChangePasswordRequest` (current_password, new_password),
`AuthSessionRead`.

Password fields carry a validator enforcing `PASSWORD_MIN_LENGTH <= len` and `<= 72 bytes`.

### 3.5 `backend/app/api/routes/auth.py` (new)

`router = APIRouter(prefix="/auth", tags=["auth"])`. Tag + function name drive the generated client
method name (`custom_generate_unique_id` -> `{tag}-{function_name}`), so `login` yields `authLogin()`.

| Method | Path | Auth | Body -> Response | Notes |
|---|---|---|---|---|
| POST | `/auth/register` | — | `RegisterRequest` -> 201 `TokenResponse` | sets refresh cookie; sends verify email via `BackgroundTasks` |
| POST | `/auth/login` | — | `LoginRequest` -> 200 `TokenResponse` | sets refresh cookie |
| POST | `/auth/refresh` | cookie | — -> 200 `RefreshResponse` | rotates the cookie |
| POST | `/auth/logout` | cookie | — -> 204 | revokes session, clears cookie |
| POST | `/auth/forgot-password` | — | `ForgotPasswordRequest` -> **202 always** | never reveals whether the address exists |
| POST | `/auth/reset-password` | — | `ResetPasswordRequest` -> 204 | consumes token, revokes **all** sessions |
| POST | `/auth/verify-email` | — | `VerifyEmailRequest` -> 204 | |
| POST | `/auth/resend-verification` | `CurrentUser` | — -> 202 | |
| POST | `/auth/change-password` | `CurrentUser` | `ChangePasswordRequest` -> 204 | revokes all *other* sessions |
| GET | `/auth/sessions` | `CurrentUser` | -> `list[AuthSessionRead]` | powers the Security settings card |
| DELETE | `/auth/sessions/{id}` | `CurrentUser` | -> 204 | |

Register in `backend/app/api/api.py`. Keep auth under its own `/auth` prefix — a literal route added
under `/users` after line 230 would be swallowed by `GET /users/{user_id}`.

Errors use `raise_problem(status, code="auth.*", detail=...)` from `app/core/errors.py`. Codes:
`auth.invalid_credentials`, `auth.email_taken`, `auth.invalid_token`, `auth.token_expired`,
`auth.rate_limited`, `auth.weak_password`, `auth.no_password_set`, `auth.session_revoked`.

### 3.6 Refresh cookie

Name from `settings.REFRESH_COOKIE_NAME`; `httponly=True`; `secure` from settings;
`samesite` from settings; `path=f"{settings.API_V1_STR}/auth"`; **no `Domain`** — host-only.
Do **not** set `Domain=.fabraham.dev`: that apex hosts other applications.

### 3.7 `backend/app/api/deps.py` (rewrite the Auth0 half only)

- Delete the `Auth0FastAPI` object and `get_or_create_user` (JIT provisioning is now explicit registration).
- New `get_access_claims` dependency reading `Authorization: Bearer` (FastAPI `HTTPBearer(auto_error=False)`), decoding via `core.security`, checking `typ == "access"`.
- **Preserve exactly**: the names `CurrentUser`, `CurrentSuperuser`, `AnyUser`, `QueryTokenUser`, `DBDep`, *and* the `Annotated[User, Depends(<callable>())]` shape — `backend/tests/fixtures/client.py:37,49,67,68` reaches in via `get_args(deps_module.CurrentUser)[1].dependency`. Break the shape and all 493 API tests silently start hitting real auth.
- **Preserve** the three `X-Test-User-Email` branches (D5), still `settings.TESTING`-gated.
- `_get_user_from_query_token` (SSE) now just decodes our own JWT — keep its deliberate short-lived `async_session.begin()` so an SSE stream does not pin a session.
- Do **not** touch `get_db`. Its commit-before-response behaviour is deliberate and documented; refresh rotation must go through `DBDep` so the rotation commits before the response.

### 3.8 Deletions

`backend/app/core/auth.py` · `backend/app/logic/auth0/` (whole package) · `_warm_auth0_cache` in
`backend/app/main.py` · `GET /users/auth0-management-url` · the `update_auth0_user` / `delete_auth0_user`
calls in `routes/users.py` (5 sites) · `auth0-fastapi-api` from `backend/pyproject.toml` ·
`scripts/setup_auth0.py` · `just setup-auth0` / `just teardown-auth0` · `docs/AUTH0.md` ·
`backend/tests/logic/test_auth0_service.py` · the Auth0-specific classes in `backend/tests/api/test_deps.py`.

`POST /users/me` becomes **`GET /users/me`** returning `UserProfile`. The `ProfileInit` schema and the
Auth0-`picture` avatar-seed path go with it (`app/logic/avatar_seed.py` stays; only the URL-seeding
call site from Auth0 goes). `UserProfile.sub` keeps its `AliasChoices` — update to `("sub", "subject")`
so the frontend identity field needs **zero** changes.

---

## 4. Configuration — `backend/app/core/config.py`

Replace the `# Auth0 configuration` block with `# Authentication`. Repurpose the three dead
template leftovers rather than adding near-duplicate names:

```python
    # Authentication
    SECRET_KEY: str = "changethis"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15        # REPURPOSED (was 60*24*8, unused)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASSWORD_MIN_LENGTH: int = 8

    # Refresh-token cookie
    REFRESH_COOKIE_NAME: str = "wirksam_refresh"
    REFRESH_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    REFRESH_COOKIE_SECURE: bool | None = None    # resolved by validator: ENVIRONMENT != "local"

    # Email-borne auth tokens
    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 1      # REPURPOSED (was 48, unused)
    EMAIL_VERIFY_TOKEN_EXPIRE_HOURS: int = 48
```

Plus `_resolve_cookie_secure` and `_enforce_non_default_secrets` as `@model_validator(mode="after")`
returning `Self`. The second revives the dead `_check_default_secret` helper (config.py:132-141) for
`SECRET_KEY`.

**`SECRET_KEY` must default to `"changethis"` and must be added to `.env.example`.** Four workflows do
`cp .env.example .env` before booting the backend; a required field with no default kills all four with a
pydantic error before a single test runs. And **never** default it to `secrets.token_urlsafe(32)` —
`backend/Dockerfile:43` runs `--workers 4`, so four processes would each mint their own key and ~3 in 4
requests would fail verification, intermittently, in production only.

Remove `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET`,
`AUTH0_MANAGEMENT_AUDIENCE` from config.py, `.env.example`, `.env.production`, and (documented, not
edited) the deploy host's `.env`.

Frontend env: delete `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, `VITE_AUTH0_API_AUDIENCE`,
`VITE_AUTH0_CALLBACK_URL` from `frontend/.env.example`, `frontend/src/env.d.ts`, `frontend/Dockerfile`
(ARG+ENV pairs) **and** `.github/workflows/deploy-production.yml:67-70` — these two halves must change
together; neither fails loudly alone. Add the long-missing `VITE_E2E_AUTH_BYPASS` to
`frontend/.env.example` while there. `E2E_AUTH0_*`, `USE_AUTH0_E2E` and the two Auth0 storageState
setup files go away.

---

## 5. Transactional email

These must **bypass** `NotificationService` entirely — it needs a seeded `NotificationType` row, writes an
in-app `Notification`, and applies the user's channel toggles, so a password reset could be silently
suppressed by a preference. It also BCC-batches, which must never touch a token-bearing mail.

`backend/app/logic/auth/emails.py`:

```python
async def send_verify_email(*, email: str, name: str | None, token: str, language: str) -> bool
async def send_password_reset_email(*, email: str, name: str | None, token: str, language: str) -> bool
```

- Links: `f"{settings.FRONTEND_HOST}/verify-email?token={token}"` and `f"{settings.FRONTEND_HOST}/reset-password?token={token}"`. `FRONTEND_HOST` is the one and only server-side base URL. No trailing-slash normalisation exists — always concatenate a leading `/`.
- Reuse the existing inline-HTML shell style from `logic/notifications/channels/email.py:_build_html` (max-width 560px, palette `#1f2937 / #f3f4f6 / #ffffff / #4b5563 / #9ca3af`), but with an arbitrary `action_url` + `action_label` and **no "manage preferences" footer** — that link is wrong on a security email.
- Transport: `aiosmtplib`, same lazy-import pattern. Gate on `settings.emails_configured` **only**, not `emails_enabled` — otherwise nothing is ever sent locally or in the e2e stack (both `ENVIRONMENT=local`), and mailcatcher (`docker-compose.override.yml`, ports 1025/1080) never receives anything. When unconfigured: `logger.warning` **and log the link** so local dev can complete the flow, then return `False`.
- Return `bool`, never raise: wrap in `try/except Exception: logger.exception(...)`. An email failure must never bubble into an HTTP response.
- Called from routes via `background_tasks.add_task(...)` with keyword args only.
- **Promote `aiosmtplib` to a direct dependency** in `backend/pyproject.toml` — it is currently only transitive via `fastapi-mail`.

Strings go in `backend/app/logic/notifications/locales/en.json` **and** `de.json` (nothing enforces parity
on these — keep them key-identical by hand). Use the newer informal German "du". Do **not** add the codes to
`registry.py` / `ALL_NOTIFICATION_TYPES` — that list is the source of truth for user-configurable toggles,
which is exactly what these mails must not be subject to.

---

## 6. Frontend

### 6.1 New: `frontend/src/lib/auth-session.ts`

A module-level singleton (**not** a Pinia store — `stores/auth.ts` constructs `useAuthenticatedClient()`,
so a store-based token source is a circular import). Holds `accessToken`, `expiresAt`, `user`,
`isAuthenticated: Ref<boolean>`, `isLoading: Ref<boolean>`. Methods: `bootstrap()`, `login()`,
`register()`, `logout()`, `refresh()`, `getAccessToken()` (auto-refreshes ~60 s before expiry and
**dedupes concurrent refreshes** behind one promise).

`bootstrap()` runs once at app start: `POST /auth/refresh` with credentials. 200 -> signed in;
401 -> anonymous. **It must resolve `isLoading` to `false` in a `finally`** — `App.vue:21` hides the entire
`<RouterView>` while `isLoading` is true, so a bootstrap that never settles renders a spinner forever
with no route at all.

### 6.2 New: `frontend/src/composables/useAuth.ts` — the drop-in for `useAuth0()`

Must expose exactly the surface the app consumes today, with **real `Ref`s** (`router/index.ts:390`
reads `authStore.session.isLoading` with **no `.value`**, relying on Pinia `reactive()` ref-unwrapping;
a plain boolean makes that busy-wait loop spin forever or never wait):

| Member | Kind |
|---|---|
| `isLoading` | `Ref<boolean>` |
| `isAuthenticated` | `Ref<boolean>` |
| `user` | `Ref<AuthUser \| undefined>` — **writable**; `stores/auth.ts:100-103` assigns to it |
| `getAccessTokenSilently()` | `() => Promise<string>` |
| `loginWithRedirect(opts?)` | pushes the router to `/login?redirect=…` |
| `logout(opts?)` | clears state, `POST /auth/logout`, navigates home |

Plus a module-level `authGuard` navigation guard replacing the Auth0 one, which additionally preserves
the intended destination as `?redirect=<fullPath>` (today it is lost entirely).

Both new files need `__tests__/*.spec.ts` at >=90 % — `vitest.config.ts` uses `perFile: true` thresholds
and a new file under `src/lib/` or `src/composables/` fails the build at 0 % coverage. Do **not** add
names to the `!(…)` carve-out lists; the comment there says those lists should only ever shrink.

### 6.3 New views (`frontend/src/views/auth/`)

`LoginView.vue`, `RegisterView.vue`, `ForgotPasswordView.vue`, `ResetPasswordView.vue`,
`VerifyEmailView.vue`. Public routes `/login`, `/register`, `/forgot-password`,
`/reset-password?token=`, `/verify-email?token=` under `NoLayout`.

Layout template: `frontend/src/views/events/InviteAcceptView.vue` — `div.flex.min-h-screen.items-center.justify-center.p-4`
containing `<Card class="w-full max-w-md">` with a centred `CardHeader`, icon, `CardTitle`, `CardDescription`,
`CardContent class="space-y-4"`, full-width buttons.

Forms: copy the **vee-validate + zod** pattern from `components/account/user/EditProfileForm.vue`
(`useForm({ validationSchema: toTypedSchema(zLoginRequest) })` + `FormField`/`FormItem`/`FormLabel`/
`FormControl`/`FormMessage`). The generated `zRegisterRequest` etc. exist after `just generate-client`.
Every shadcn component needed is already installed.

Also: `ChangePasswordCard.vue` and `ActiveSessionsCard.vue` in `components/account/user/`, replacing
`PasswordResetCard.vue` (which talks to Auth0 with raw axios, bypassing the generated client).

Every interactive element gets a `data-testid`; the page `h1` carries `data-testid="page-heading"`.

### 6.4 Modified

`main.ts` (drop `createAuth0`, add `withCredentials: true` to `client.setConfig` — without it the httpOnly
refresh cookie is never sent; call `bootstrap()`), `App.vue`, `stores/auth.ts` (rename the re-exported
`auth0` property to `session`; `loadProfile()` now `GET /users/me` with no upsert body),
`useAuthenticatedClient.ts`, `router/index.ts` (new routes + new guard; add any authenticated new routes to
`SELECTED_EVENT_EXEMPT_ROUTES`), `PreAuthHeader.vue`, `LandingView.vue`,
`UserSettingsView.vue`, `CurrentProfileCard.vue`, `EditProfileForm.vue`, `env.d.ts`, `package.json`
(drop `@auth0/auth0-vue`), `Dockerfile`, `.env.example`.

Deleted: `components/account/user/useAuthProvider.ts` (check whether `simple-icons` / `SimpleIcon.vue`
become orphaned), `PasswordResetCard.vue`. `src/testing/fake-auth0.ts` becomes `src/testing/fake-session.ts`
providing the same shape against the new composable, still keyed on `VITE_E2E_AUTH_BYPASS` +
`e2e_bypass=1`, still setting `wirksam-last-seen-changelog=99.99.99` and `locale=en`.

### 6.5 i18n

New namespace **`auth.json`** in **both** `frontend/src/locales/en/` and `de/` (the filename is the
top-level message key, so `$t('auth.login.title')`). New `errorCodes.json` entries for every `auth.*`
problem code. Keys alphabetically sorted. Parity is CI-gated by
`scripts/pre-commit/check_locale_parity.js` (file parity, key parity, value type, empty values,
placeholder drift, plural-branch drift).

---

## 7. Traps (each of these fails silently)

- **G1 — `demo|` is behavioural.** `logic/notifications/channels/{email,push,telegram}.py` all do `recipient.auth0_sub.startswith("demo|")` to avoid emailing fake demo users. The rename must land in the same commit or demo accounts start receiving real mail. basedpyright strict catches it *if you run it*.
- **G2 — `test|` drives E2E cleanup.** `POST /testing/reset` deletes users by that prefix. Break it and the suite either starts dirty or wipes a developer's local DB.
- **G3 — `ondelete="SET NULL"` on a user FK is forbidden** in this schema; both new tables use CASCADE. Regression coverage: `tests/api/routes/test_event_members.py::TestUserDeletionCascades`.
- **G4 — datetimes are naive UTC.** `datetime.now(timezone.utc).replace(tzinfo=None)`. Comparing a naive `expires_at` to an aware `now()` raises `TypeError` at runtime, in the refresh path, under load.
- **G5 — coverage gates fire in the same PR.** `fail_under = 95` aggregate **and** `diff-cover --fail-under=90` on changed lines. Deleting ~1600 lines of well-covered Auth0 tests while adding heavily-branching new auth code is the fastest way to red-line `dev`. Ship tests with the code.
- **G6 — `alembic check` is a CI gate**, and the pytest session builds `app_test` by running `alembic upgrade head` in a subprocess: a model change without a migration fails the *entire* suite at session setup with a confusing error.
- **G7 — `throwOnError: true`** (`main.ts:16`) means a 401 from `/auth/login` **throws** an `AxiosError`. Write the handlers accordingly; surface via `toastApiError(e)`.
- **G8 — `e2e/COVERAGE.md` is diff-checked** by `lint-frontend.yml`. Adding or renaming any spec without `just generate-e2e-coverage` fails the frontend lint job with an unrelated-looking message.
- **G9 — never `waitUntil: 'networkidle'`** in E2E: the SSE `/notifications/stream` endpoint holds a connection open forever.
- **G10 — `.env.production` sits in the working tree** (gitignored) holding a live Auth0 client secret, SMTP password, Postgres password and Telegram token. Declaring `SECRET_KEY` makes its line 15 the live production signing key — it has been inert until now because `extra="ignore"` discarded it. **Rotate it.** Never echo these values into logs, tests or artifacts.
- **G11 — the deploy host's `.env` is hand-maintained and outside this repo.** It must gain `SECRET_KEY` *before* the first post-migration release, or `prestart` fails `Settings()` construction and the deploy hangs 120 s at the health-wait.
- **G12 — `env_ignore_empty=True`**: `KEY=` in an env file falls back to the field default, not `""`. Write `SECRET_KEY=changethis`, not `SECRET_KEY=`.

---

## 8. Docs to update (or Auth0 idioms get copy-pasted back in weeks later)

`CLAUDE.md` (Auth Pattern section) · `AGENTS.md` · `backend/app/api/routes/README.md` ·
`docs/SECURITY.md` · `README.md` · delete `docs/AUTH0.md`, add `docs/AUTH.md`.

## 9. Post-change ritual

`just generate-client` (never hand-edit `frontend/src/client/`) · `uv run --directory backend alembic check` ·
`uv run basedpyright` with **no arguments** from inside `backend/` · `just lint` ·
`just test-backend` · `pnpm --prefix frontend test:unit:coverage` · `just generate-e2e-coverage`.
