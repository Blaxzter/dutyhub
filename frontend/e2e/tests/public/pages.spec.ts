/**
 * Header navigation on the pre-auth pages.
 *
 * About and How It Works are sections of the landing page rather than routes
 * of their own, so the header links set a hash instead of pushing a new view.
 */
import { expect, test } from '@playwright/test'

test.describe('public pages', () => {
  test('header links jump to the landing page sections', async ({ page }) => {
    await page.goto('/')

    const header = page.getByRole('banner')
    await header.getByRole('button', { name: /how it works|so funktioniert/i }).click()
    await expect(page).toHaveURL(/#how-it-works$/)
    await expect(page.locator('#how-it-works')).toBeInViewport()
  })

  test('a legal page can navigate back into a landing section', async ({ page }) => {
    await page.goto('/privacy')

    const header = page.getByRole('banner')
    await header.getByRole('button', { name: /about|über/i }).click()
    await expect(page).toHaveURL(/\/#about$/)
    await expect(page.locator('#about')).toBeVisible()
  })
})
