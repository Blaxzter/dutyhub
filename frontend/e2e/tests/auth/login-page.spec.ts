/**
 * The sign-in screen as an anonymous visitor meets it.
 *
 * It is the only door into the app, so "can it be reached, and can it be used"
 * is worth asserting on its own — separately from whether a password works. The
 * axe scan lives here rather than with the other a11y specs because those all
 * run as somebody who is already signed in, and this page only exists for
 * somebody who is not.
 */
import { expect, test } from '../../fixtures.js'
import { expectNoA11yViolations, tabUntilFocused } from '../../helpers/a11y.js'
import { pinBrowserPreferences } from '../../helpers/auth.js'

test.use({ storageState: { cookies: [], origins: [] } })

test.beforeEach(async ({ page }) => {
  await pinBrowserPreferences(page)
})

test.describe('Auth – the sign-in screen when signed out', () => {
  test('is reachable by URL and asks for an address and a password', async ({ page }) => {
    await page.goto('/login')

    await expect(page.getByTestId('page-heading')).toBeVisible()
    await expect(page.getByTestId('login-form')).toBeVisible()
    await expect(page.getByTestId('input-email')).toBeVisible()
    await expect(page.getByTestId('input-password')).toBeVisible()
    await expect(page.getByTestId('btn-login')).toBeEnabled()
  })

  test('offers the way on to registration', async ({ page }) => {
    await page.goto('/login')

    await page.getByTestId('link-register').click()
    await expect(page).toHaveURL(/\/register/)
    await expect(page.getByTestId('register-form')).toBeVisible()

    await page.getByTestId('link-login').click()
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByTestId('login-form')).toBeVisible()
  })

  test('keeps the password hidden until it is asked for', async ({ page }) => {
    await page.goto('/login')
    const password = page.getByTestId('input-password')
    await password.fill('not-the-real-one')

    await expect(password).toHaveAttribute('type', 'password')
    await page.getByTestId('btn-toggle-password').click()
    await expect(password).toHaveAttribute('type', 'text')
    await page.getByTestId('btn-toggle-password').click()
    await expect(password).toHaveAttribute('type', 'password')
  })

  test('can be filled in from the keyboard alone', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByTestId('login-form')).toBeVisible()

    // Somebody who cannot use a pointer still has to be able to sign in, so
    // both fields and the submit button must sit on the tab order in that
    // order. `tabUntilFocused` reports where focus actually landed when they do
    // not, which is the only useful thing a failure here can say.
    await tabUntilFocused(page, '[data-testid="input-email"]')
    await page.keyboard.press('Tab')
    await expect(page.getByTestId('input-password')).toBeFocused()
  })

  test('has no serious or critical accessibility violations', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByTestId('page-heading')).toBeVisible()
    await expectNoA11yViolations(page, { label: 'sign in (/login)' })
  })

  test('the registration screen has none either', async ({ page }) => {
    await page.goto('/register')
    await expect(page.getByTestId('page-heading')).toBeVisible()
    await expectNoA11yViolations(page, { label: 'register (/register)' })
  })

  test('nor does the password-recovery screen', async ({ page }) => {
    await page.goto('/forgot-password')
    await expect(page.getByTestId('page-heading')).toBeVisible()
    await expectNoA11yViolations(page, { label: 'forgot password (/forgot-password)' })
  })
})
