/**
 * The E2E sign-in bypass.
 *
 * Makes the SPA believe it is signed in without a password, a token or a round
 * trip. It is only half of the story: the *real* identity is asserted
 * server-side by the `X-Test-User-Email` header the Playwright fixture injects
 * into every `/api/v1/**` request, against a backend running with `TESTING=true`.
 * So nothing here needs to be a credential — the fake token below is never
 * checked, and could not be forged into anything if it were.
 *
 * Why the bypass survived the move to our own authentication: in CI the browser
 * origin and `VITE_API_URL=http://backend:8787` are genuinely cross-site, so a
 * `SameSite=Lax` refresh cookie is silently dropped, and `SameSite=None`
 * requires `Secure` requires HTTPS. A real-login E2E suite would pass on a
 * developer's machine and fail in CI, which is the worst of both.
 *
 * Installed from `main.ts` behind two gates that must both be open:
 * `VITE_E2E_AUTH_BYPASS === 'true'` at build time, and an `e2e_bypass=1` cookie
 * on the run.
 */
import { authSession } from '@/lib/auth-session'
import type { AuthUser } from '@/lib/auth-session'
import i18n from '@/locales/i18n'

/**
 * localStorage key the Playwright fixture writes the impersonated user to,
 * as JSON: `{ "email": "…", "name": "…" }`. Everything else is derived or
 * defaulted, so the fixture only has to know the two fields it seeded the
 * backend with.
 */
const USER_KEY = 'wirksam-e2e-user'
const CHANGELOG_KEY = 'wirksam-last-seen-changelog'
const LOCALE_KEY = 'locale'

const DEFAULT_EMAIL = 'default@test.example.com'
const DEFAULT_NAME = 'Test User'

/** Far enough out that no test run ever reaches the refresh path. */
const FAKE_TOKEN_LIFETIME_SECONDS = 86_400

function readSeededUser(): AuthUser {
  let seeded: Partial<AuthUser> = {}
  try {
    const raw = localStorage.getItem(USER_KEY)
    if (raw) seeded = JSON.parse(raw) as Partial<AuthUser>
  } catch {
    // A malformed entry is a broken fixture, not a reason to fail the run
    // before the first assertion — fall through to the default identity.
  }

  const email = seeded.email ?? DEFAULT_EMAIL
  return {
    // `test|` is behavioural, not decoration: `POST /testing/reset` deletes
    // users by that prefix, and the notification channels refuse to send real
    // mail to it.
    sub: seeded.sub ?? `test|${email}`,
    email,
    name: seeded.name ?? DEFAULT_NAME,
    email_verified: seeded.email_verified ?? true,
    picture: seeded.picture ?? '',
  }
}

/**
 * Two browser preferences that decide whether the suite can see the app at all.
 */
function seedTestPreferences(): void {
  // "What's New" opens over the whole UI the first time a browser sees a new
  // version and swallows the clicks of every spec behind it. A version no
  // release will ever reach means it never opens.
  localStorage.setItem(CHANGELOG_KEY, '99.99.99')

  // The specs assert English copy. With nothing stored the app follows the
  // browser's language, so a German-configured machine renders a German UI that
  // matches none of them. Only a default: a spec that deliberately stores `de`
  // keeps it. The live locale is set as well as the stored one because i18n
  // read localStorage when it was imported, which is before this runs.
  if (!localStorage.getItem(LOCALE_KEY)) {
    localStorage.setItem(LOCALE_KEY, 'en')
    i18n.global.locale.value = 'en'
  }
}

export function installFakeSession(): void {
  seedTestPreferences()

  authSession.setSession({
    access_token: 'fake-test-token',
    expires_in: FAKE_TOKEN_LIFETIME_SECONDS,
    user: readSeededUser(),
  })

  // `bootstrap()` exists to ask the server "is anybody signed in?", and here
  // the answer is already yes. Left alone it would POST /auth/refresh with no
  // cookie, take the 401 as "anonymous" and tear this session down again on the
  // first navigation — the route guard awaits it, so every spec would land on
  // the login page instead of the app.
  authSession.bootstrap = async () => {}
}
