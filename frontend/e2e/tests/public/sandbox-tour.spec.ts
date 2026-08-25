import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

/**
 * The guided tour, end to end.
 *
 * The single thing worth testing here is that the tour **survives navigation**.
 * Every step lives in a fresh view: `PostAuthLayout` keys its `RouterView` on
 * the route, so crossing from the dashboard to the task list destroys the
 * element the popover was anchored to. The tour keeps its place in a Pinia
 * store mirrored to `sessionStorage`, destroys the driver before each push and
 * re-queries the anchor on the other side — and if any of that regresses, the
 * symptom is a popover that silently stops appearing partway through, which no
 * unit test would catch.
 */

async function startDemo(page: Page, role: 'helper' | 'manager') {
  await page.goto('/')
  await page.getByTestId('btn-cta-demo').click()
  await expect(page.getByTestId('dialog-sandbox-start')).toBeVisible()
  await page.getByTestId(`btn-sandbox-role-${role}`).click()
  await page.getByTestId('btn-sandbox-start').click()
  await page.waitForURL(/\/app\//, { timeout: 30_000 })
}

async function exitDemo(page: Page) {
  await page
    .locator('.driver-popover-close-btn')
    .click({ timeout: 3000 })
    .catch(() => {})
  await page.getByTestId('btn-sandbox-exit').click()
  await page.getByTestId('btn-dialog-confirm').click()
  await page.waitForURL(/\/$/, { timeout: 15_000 })
}

/**
 * Click Next and wait for the step counter to actually change.
 *
 * A fixed timeout is not good enough: a step whose `before()` hook opens a
 * dialog takes noticeably longer than one that only moves the highlight, and
 * waiting a flat two seconds makes the walk race the slow ones.
 * Returns false once the tour has finished.
 */
async function nextStep(page: Page): Promise<boolean> {
  const next = page.locator('.driver-popover-next-btn')
  if (!(await next.isVisible().catch(() => false))) return false

  const before = ((await page.locator('.driver-popover-progress-text').textContent()) ?? '').trim()
  const isLast = /done|finish|fertig/i.test((await next.textContent()) ?? '')
  await next.click()
  if (isLast) return false

  await page.waitForFunction(
    (previous) => {
      const el = document.querySelector('.driver-popover-progress-text')
      return !!el?.textContent && el.textContent.trim() !== previous
    },
    before,
    { timeout: 20_000 },
  )
  return true
}

/**
 * The `n` out of `tour.common.progress`, whichever locale rendered it.
 *
 * Parsed rather than compared to a literal because the counter is translated
 * and the tracks are still gaining and losing steps; the number is the only
 * part of that string this file has any business knowing.
 */
async function stepNumber(page: Page): Promise<number> {
  const text = (await page.locator('.driver-popover-progress-text').textContent()) ?? ''
  return Number(text.match(/\d+/)?.[0] ?? NaN)
}

/**
 * Press Next, then press it twice more without waiting to be invited.
 *
 * Returns whether the tour had greyed the button out by then — which is the
 * only case worth asserting about. A step whose anchor is already on screen
 * settles inside a microtask, so three deliberate presses at that one really
 * are three presses; a step that has to navigate, or open a dialog, is busy
 * for long enough that the popover still on screen belongs to the step before
 * it, and every extra press used to walk the store forward again, skipping the
 * step being prepared without ever showing it.
 *
 * Lives out here rather than inline because `playwright/no-conditional-in-test`
 * is right about branches in test bodies.
 */
async function pressNextImpatiently(page: Page): Promise<boolean> {
  const next = page.locator('.driver-popover-next-btn')
  await next.click()

  if (!(await next.isDisabled().catch(() => false))) return false

  // `force`, because Playwright would otherwise wait politely for the button to
  // come back and there would be nothing left to prove. Bypassing actionability
  // is the assertion here, not a way around a flaky selector — which is what
  // the rule below is normally right to object to.
  /* eslint-disable playwright/no-force-option */
  await next.click({ force: true, timeout: 2000 }).catch(() => {})
  await next.click({ force: true, timeout: 2000 }).catch(() => {})
  /* eslint-enable playwright/no-force-option */
  return true
}

/** Walk a whole track, returning the route each step landed on. */
async function walk(page: Page, maxSteps: number): Promise<string[]> {
  await expect(page.locator('.driver-popover-title')).toBeVisible({ timeout: 20_000 })

  const routes: string[] = []
  for (let i = 0; i < maxSteps; i++) {
    // The popover must be present at every single step — this is the assertion
    // the whole spec exists for.
    await expect(page.locator('.driver-popover-title')).toBeVisible()
    routes.push(new URL(page.url()).pathname)
    if (!(await nextStep(page))) break
  }
  return routes
}

test.describe('guided tour', () => {
  // Walking a whole track means a dozen real navigations and page loads.
  test.slow()

  test('the helper track starts on its own and runs to the end across routes', async ({ page }) => {
    await startDemo(page, 'helper')

    const routes = await walk(page, 15)

    // It got somewhere, and it crossed route boundaries to do it.
    expect(routes.length).toBeGreaterThanOrEqual(5)
    expect(new Set(routes).size).toBeGreaterThan(1)
    expect(routes.some((r) => r.includes('/app/tasks'))).toBe(true)

    // Finishing closes the tour rather than leaving an overlay behind.
    await expect(page.locator('.driver-popover')).toBeHidden()

    await exitDemo(page)
  })

  test('the organiser track covers the management screens', async ({ page }) => {
    await startDemo(page, 'manager')

    const routes = await walk(page, 20)

    expect(routes.length).toBeGreaterThanOrEqual(8)
    expect(routes.some((r) => r.includes('/app/tasks'))).toBe(true)
    expect(routes.some((r) => r.includes('/app/reporting'))).toBe(true)

    await expect(page.locator('.driver-popover')).toBeHidden()

    await exitDemo(page)
  })

  test('presses land one step at a time while a step is still opening', async ({ page }) => {
    await startDemo(page, 'helper')
    await expect(page.locator('.driver-popover-title')).toBeVisible({ timeout: 20_000 })

    // Five presses reach `bookShift`, whose `before()` hook has to click a
    // shift chip and wait for a dialog — comfortably the slowest transition in
    // the track, and the one this is really about. The others are here because
    // a route push is slow enough to click through as well.
    const busy: boolean[] = []
    for (let i = 0; i < 5; i++) {
      const before = await stepNumber(page)

      busy.push(await pressNextImpatiently(page))

      await expect.poll(() => stepNumber(page), { timeout: 25_000 }).toBe(before + 1)
      await expect(page.locator('.driver-popover-next-btn')).toBeEnabled()
    }

    // If nothing ever reported itself busy the loop above proved nothing, so
    // this is as much a check on the test as on the tour.
    expect(busy).toContain(true)

    await exitDemo(page)
  })

  test('the banner can restart a tour that was closed', async ({ page }) => {
    await startDemo(page, 'helper')

    await expect(page.locator('.driver-popover')).toBeVisible({ timeout: 20_000 })
    await page.locator('.driver-popover-close-btn').click()
    await expect(page.locator('.driver-popover')).toBeHidden()

    await page.getByTestId('btn-sandbox-tour').click()
    await expect(page.locator('.driver-popover')).toBeVisible({ timeout: 20_000 })

    await exitDemo(page)
  })
})
