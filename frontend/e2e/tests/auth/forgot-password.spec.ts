/**
 * Asking for a password-reset link.
 *
 * The endpoint answers 202 whether or not the address belongs to anybody, and
 * the screen has to keep that promise — otherwise the form becomes a membership
 * oracle: type an address, learn whether that person volunteers here. So the
 * test that matters is not "a confirmation appears" but "the *same* confirmation
 * appears", which is why the two answers are compared to each other rather than
 * to a hard-coded sentence.
 */
import type { Page } from '@playwright/test'

import { expect, test } from '../../fixtures.js'
import { authTestEmail, pinBrowserPreferences } from '../../helpers/auth.js'

test.use({ storageState: { cookies: [], origins: [] } })

/**
 * Submit the form and return what it said, with the address blanked out.
 *
 * The confirmation quotes the address back — that is the one thing the two
 * answers are *allowed* to differ by, so it is masked before they are compared.
 */
async function requestResetLink(page: Page, email: string): Promise<string> {
  await page.goto('/forgot-password')
  await expect(page.getByTestId('forgot-password-form')).toBeVisible()

  await page.getByTestId('input-email').fill(email)
  await page.getByTestId('btn-forgot-password-submit').click()

  const confirmation = page.getByTestId('forgot-password-sent')
  await expect(confirmation).toBeVisible()
  const text = await confirmation.innerText()
  return text.split(email).join('{address}')
}

test.describe('Auth – forgot password', () => {
  test('a known and an unknown address get the same answer', async ({
    adminUser,
    page,
  }, testInfo) => {
    await pinBrowserPreferences(page)

    // A real account. Asking for a reset link is not destructive — it mints a
    // token nothing in this spec redeems, and leaves the password alone — so
    // the worker's shared admin is safe to use.
    const known = await requestResetLink(page, adminUser.email)

    // An address that has never been registered.
    const unknown = await requestResetLink(page, authTestEmail(testInfo))

    expect(unknown).toBe(known)
    // And neither answer volunteers the fact one way or the other.
    expect(known.toLowerCase()).not.toMatch(/no (such )?account|not found|unknown|doesn't exist/)
  })

  test('the confirmation is reachable from the sign-in form', async ({ page }) => {
    await pinBrowserPreferences(page)
    await page.goto('/login')

    await page.getByTestId('link-forgot-password').click()
    await expect(page).toHaveURL(/\/forgot-password/)
    await expect(page.getByTestId('page-heading')).toBeVisible()

    // And back again, so somebody who clicked it by mistake is not stranded.
    await page.getByTestId('link-back-to-login').click()
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByTestId('login-form')).toBeVisible()
  })
})
