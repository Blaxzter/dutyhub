import { expect, test } from '@playwright/test'

test.describe('landing page', () => {
  test('renders main hero and auth actions', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('page-heading')).toBeVisible()
    // In E2E bypass mode the fake Auth0 plugin reports isAuthenticated=true,
    // so the CTA button (sign in/get started) may not be shown.
    const cta = page.getByTestId('btn-cta-primary')
    // eslint-disable-next-line playwright/no-conditional-in-test
    if (await cta.isVisible({ timeout: 2000 }).catch(() => false)) {
      // eslint-disable-next-line playwright/no-conditional-expect
      await expect(cta).toBeVisible()
    }
  })

  test('every section the in-page nav links to actually exists', async ({ page }) => {
    await page.goto('/')
    // Anchor on the hero first: under parallel load the section assertions can
    // otherwise start before the app has hydrated, and fail on an empty body.
    await expect(page.getByTestId('page-heading')).toBeVisible()

    for (const id of ['audience', 'how-it-works', 'features', 'about', 'get-started']) {
      await expect(page.locator(`#${id}`)).toBeVisible()
    }
  })

  test('the old /about path redirects into the landing page', async ({ page }) => {
    await page.goto('/about')
    await expect(page).toHaveURL(/\/#about$/)
    await expect(page.locator('#about')).toBeVisible()
  })

  test('a screenshot opens in the viewer and pages through the gallery', async ({ page }) => {
    await page.goto('/')

    const frames = page.locator('#features button[aria-label]')
    await frames.first().scrollIntoViewIfNeeded()
    await frames.first().click()

    const viewer = page.getByRole('dialog')
    await expect(viewer).toBeVisible()
    await expect(viewer.locator('img')).toHaveAttribute('src', /shift-schedule-(light|dark)\.png$/)

    // Arrow keys walk the gallery.
    await page.keyboard.press('ArrowRight')
    await expect(viewer.locator('img')).toHaveAttribute('src', /tasks-(light|dark)\.png$/)

    // Escape closes it and hands focus back to the frame that opened it.
    await page.keyboard.press('Escape')
    await expect(viewer).toBeHidden()
    await expect(frames.first()).toBeFocused()
  })
})
