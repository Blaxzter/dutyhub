import { expect, test } from '@playwright/test'

test.describe('landing page', () => {
  test('renders main hero and auth actions', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('page-heading')).toBeVisible()
    // `btn-cta-primary` is on both branches of the hero — "get started" for an
    // anonymous visitor, "go to dashboard" for a signed-in one — so it is
    // present either way and the assertion needs no escape hatch.
    await expect(page.getByTestId('btn-cta-primary')).toBeVisible()
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
