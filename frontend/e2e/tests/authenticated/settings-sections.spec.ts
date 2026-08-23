/**
 * E2E smoke tests for individual Settings sections.
 */
import { expect, test } from '../../fixtures.js'

test.describe('Settings – profile section', () => {
  test('can navigate to profile section', async ({ adminPage: page }) => {
    await page.goto('/app/settings/profile')
    await expect(page).toHaveURL(/\/app\/settings\/profile/)
  })

  test('shows profile section content', async ({ adminPage: page }) => {
    await page.goto('/app/settings/profile')
    await expect(page.getByTestId('section-profile')).toBeVisible()
  })
})

// Both of these used to be skipped unless `USE_AUTH0_E2E=true`: the section was
// a link out to Auth0's own password page and had nothing of its own to show.
// It is now two cards this app renders and owns.
test.describe('Settings – security section', () => {
  test('can navigate to security section', async ({ adminPage: page }) => {
    await page.goto('/app/settings/security')
    await expect(page).toHaveURL(/\/app\/settings\/security/)
  })

  test('shows security section content', async ({ adminPage: page }) => {
    await page.goto('/app/settings/security')
    await expect(page.getByTestId('section-security')).toBeVisible()
    await expect(page.getByTestId('change-password-card')).toBeVisible()
    await expect(page.getByTestId('active-sessions-card')).toBeVisible()
  })
})

test.describe('Settings – data export section', () => {
  test('can navigate to data section', async ({ adminPage: page }) => {
    await page.goto('/app/settings/dataPrivacy')
    await expect(page).toHaveURL(/\/app\/settings\/dataPrivacy/)
  })

  test('shows data section content', async ({ adminPage: page }) => {
    await page.goto('/app/settings/dataPrivacy')
    await expect(page.getByTestId('section-dataPrivacy')).toBeVisible()
  })
})

test.describe('Settings – language section', () => {
  test('can navigate to language section', async ({ adminPage: page }) => {
    await page.goto('/app/settings/language')
    await expect(page).toHaveURL(/\/app\/settings\/language/)
  })

  test('shows language section content', async ({ adminPage: page }) => {
    await page.goto('/app/settings/language')
    await expect(page.getByTestId('section-language')).toBeVisible()
  })
})
