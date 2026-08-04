/**
 * Accessibility scans of the public (pre-auth) pages.
 *
 * These use the plain `page` fixture — no auth bypass — so the scan sees what an
 * anonymous visitor sees. storageState is cleared explicitly so the Auth0-mode
 * project's admin session cannot leak in and change what renders.
 */
import { expect, test } from '@playwright/test'

import { expectNoA11yViolations } from '../../helpers/a11y.js'

test.use({ storageState: { cookies: [], origins: [] } })

test.describe('a11y – public pages', () => {
  test('landing page has no serious or critical violations', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('page-heading')).toBeVisible()
    await expectNoA11yViolations(page, { label: 'landing (/)' })
  })

  test('about page has no serious or critical violations', async ({ page }) => {
    await page.goto('/about')
    await expect(page.getByTestId('page-heading')).toBeVisible()
    await expectNoA11yViolations(page, { label: 'about (/about)' })
  })

  test('how-it-works page has no serious or critical violations', async ({ page }) => {
    await page.goto('/how-it-works')
    await expect(page.getByTestId('page-heading')).toBeVisible()
    await expectNoA11yViolations(page, { label: 'how it works (/how-it-works)' })
  })
})
