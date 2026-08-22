/**
 * E2E tests for the How It Works content.
 *
 * It used to be a page of its own. It is now a section of the landing page,
 * and `/how-it-works` is kept as a redirect because the old path was linked
 * from outside the app — so that redirect is what these tests guard.
 */
import { expect, test } from '@playwright/test'

test.describe('How It Works section', () => {
  test('the old /how-it-works path redirects to the landing section', async ({ page }) => {
    await page.goto('/how-it-works')
    await expect(page).toHaveURL(/\/#how-it-works$/)
  })

  test('shows both the organiser and volunteer journeys', async ({ page }) => {
    await page.goto('/how-it-works')

    const section = page.locator('#how-it-works')
    await expect(section).toBeVisible()

    // Organiser is the default track; the volunteer track is one tab away.
    await expect(section.getByRole('tab', { selected: true })).toBeVisible()
    await expect(section.getByRole('listitem').first()).toBeVisible()

    const tabs = section.getByRole('tab')
    await tabs.nth(1).click()
    await expect(tabs.nth(1)).toHaveAttribute('aria-selected', 'true')
    await expect(section.getByRole('listitem').first()).toBeVisible()
  })
})
