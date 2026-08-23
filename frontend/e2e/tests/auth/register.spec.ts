/**
 * Creating an account, through the real form and the real endpoint.
 *
 * Everything else in the suite is already signed in before its first line runs.
 * This is the one place that watches somebody arrive with nothing — no cookie,
 * no session, no account — and end up inside the app.
 */
import { expect, serverApiRaw, test } from '../../fixtures.js'
import {
  AUTH_TEST_PASSWORD,
  authTestEmail,
  deleteAccount,
  pinBrowserPreferences,
} from '../../helpers/auth.js'

// No session may leak in: an authenticated visitor is bounced straight off
// /register by the router guard, and the test would fail on a redirect rather
// than on anything it meant to check.
test.use({ storageState: { cookies: [], origins: [] } })

// The account this spec creates registers with a password, so its subject is
// `local|…` and `POST /testing/reset` leaves it alone. The address is derived
// from the test, so this also clears up after a run that crashed before it.
test.afterEach(async ({ adminUser }, testInfo) => {
  await deleteAccount(adminUser.email, authTestEmail(testInfo)).catch(() => {})
})

test.describe('Auth – registration', () => {
  test('a new account signs straight in and lands in the app', async ({
    adminUser,
    page,
  }, testInfo) => {
    const email = authTestEmail(testInfo)

    await pinBrowserPreferences(page)
    await page.goto('/register')
    await expect(page.getByTestId('page-heading')).toBeVisible()

    await page.getByTestId('input-name').fill('Registration Test')
    await page.getByTestId('input-email').fill(email)
    await page.getByTestId('input-password').fill(AUTH_TEST_PASSWORD)
    await page.getByTestId('input-confirm-password').fill(AUTH_TEST_PASSWORD)
    await page.getByTestId('btn-register').click()

    // Registration answers with an access token, so there is no "confirm your
    // address first" wall in the way. A brand-new account belongs to no event
    // yet, so the router sends it to the event picker rather than the
    // dashboard — both live under /app and both render a page heading, and
    // which one it is belongs to the onboarding tests, not to this one.
    await page.waitForURL(/\/app\//)
    await expect(page.getByTestId('page-heading')).toBeVisible()

    // The account is real, not just a client-side illusion: the platform admin
    // can see it.
    const found = await serverApiRaw(
      'GET',
      `/users/?q=${encodeURIComponent(email)}`,
      adminUser.email,
    )
    expect(found.status).toBe(200)
    const items = (found.body as { items: { email: string | null }[] }).items
    expect(items.map((item) => item.email)).toContain(email)
  })

  test('registering twice with the same address is refused', async ({ page }, testInfo) => {
    const email = authTestEmail(testInfo)
    // The address is taken before the form is ever opened, so the refusal comes
    // from the endpoint rather than from a second pass through the UI.
    const taken = await serverApiRaw('POST', '/auth/register', '', {
      email,
      name: 'Already Registered',
      password: AUTH_TEST_PASSWORD,
      preferred_language: 'en',
    })
    expect(taken.status).toBe(201)

    await pinBrowserPreferences(page)
    await page.goto('/register')
    await page.getByTestId('input-name').fill('Second Attempt')
    await page.getByTestId('input-email').fill(email)
    await page.getByTestId('input-password').fill(AUTH_TEST_PASSWORD)
    await page.getByTestId('input-confirm-password').fill(AUTH_TEST_PASSWORD)
    await page.getByTestId('btn-register').click()

    // `errorCodes.auth.email_taken` — the problem code the endpoint answers
    // with, translated by `lib/api-errors.ts`.
    await expect(page.locator('[data-sonner-toast]')).toContainText(
      'An account already exists for this email address.',
    )
    await expect(page).toHaveURL(/\/register/)
  })
})
