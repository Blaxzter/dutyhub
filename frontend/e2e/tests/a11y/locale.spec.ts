/**
 * The same authenticated page, scanned in both locales.
 *
 * A missing or empty translation can produce an empty `aria-label`, an
 * unlabelled button or a link with no discernible text. The i18n key-parity
 * check compares en/de key sets — it cannot see what the rendered DOM does with
 * a blank value, and the English scan will not catch it either.
 *
 * Forcing German: the app boots its locale from `localStorage.locale`
 * (see `src/locales/i18n.ts`) and then posts that value to `/users/me` as the
 * user's `preferred_language`. The fixtures seed `en` from a context-level init
 * script; a page-level init script runs after it, so writing `de` there and
 * reloading is enough — no API poking, no race with profile loading.
 */
import { expect, test } from '../../fixtures.js'
import { expectNoA11yViolations } from '../../helpers/a11y.js'
import { api } from '../../helpers/api.js'

test.describe('a11y – locales', () => {
  test.afterEach(async ({ adminPage: page }) => {
    // Worker users are reused by later tests; put the language back.
    await api(page, 'PATCH', '/users/me', { preferred_language: 'en' }).catch(() => {})
  })

  test('dashboard in English', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-my-bookings')).toContainText('My Bookings')
    await expectNoA11yViolations(page, { label: 'admin dashboard, locale=en' })
  })

  test('dashboard in German', async ({ adminPage: page }) => {
    await page.addInitScript(() => localStorage.setItem('locale', 'de'))
    await page.goto('/app/home')

    // Prove the page really switched — otherwise this is a duplicate English scan.
    await expect(page.getByTestId('sidebar-link-my-bookings')).toContainText('Meine Buchungen')
    await expectNoA11yViolations(page, { label: 'admin dashboard, locale=de' })
  })
})
