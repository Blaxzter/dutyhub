import { mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import { expect, test as setup } from '@playwright/test'

const authFile = 'e2e/.auth/member.json'

setup('authenticate member with Auth0', async ({ page }) => {
  const username = process.env.E2E_AUTH0_USERNAME_MEMBER
  const password = process.env.E2E_AUTH0_PASSWORD_MEMBER

  if (!username || !password) {
    throw new Error(
      'Missing E2E member credentials. Set E2E_AUTH0_USERNAME_MEMBER and E2E_AUTH0_PASSWORD_MEMBER before running Playwright.',
    )
  }

  await page.goto('/')
  await page.getByRole('button', { name: /sign in|get started/i }).first().click()

  const usernameInput = page
    .locator('input[name="username"], input#username, input[type="email"]')
    .first()
  await usernameInput.waitFor({ state: 'visible', timeout: 45_000 })
  await usernameInput.fill(username)

  const passwordInput = page
    .locator('input[name="password"], input#password, input[type="password"]')
    .first()

  const passwordVisible = await passwordInput.isVisible({ timeout: 2_000 }).catch(() => false)
  if (!passwordVisible) {
    const continueButton = page.getByRole('button', { name: /continue|next/i }).first()
    if (await continueButton.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await continueButton.click()
    }
  }

  await passwordInput.waitFor({ state: 'visible', timeout: 45_000 })
  await passwordInput.fill(password)

  const submitButton = page.getByRole('button', { name: /continue|log in|login|sign in/i }).first()
  if (await submitButton.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await submitButton.click()
  } else {
    await page.locator('button[type="submit"], button[name="action"]').first().click()
  }

  const consentButton = page.getByRole('button', { name: /accept|authorize|allow/i }).first()
  if (await consentButton.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await consentButton.click()
  }

  await page.waitForURL(/\/app\/home/, { timeout: 60_000 })
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: 30_000 })

  mkdirSync(dirname(authFile), { recursive: true })
  await page.context().storageState({ path: authFile })
})
