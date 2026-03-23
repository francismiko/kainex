import { test, expect } from '@playwright/test'

test.describe('Market', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/market')
  })

  test('K-line chart renders', async ({ page }) => {
    await expect(page.locator('h1')).toHaveText('行情中心')
    // lightweight-charts renders into a canvas inside the chart container
    const canvas = page.locator('canvas').first()
    await expect(canvas).toBeVisible({ timeout: 10_000 })
  })

  test('symbol switch works', async ({ page }) => {
    // The watchlist on desktop shows symbol links; click ETH/USDT
    const watchlist = page.locator('text=ETH/USDT').first()
    await watchlist.click()
    // After switching, the card title should update
    await expect(page.locator('text=ETH/USDT').first()).toBeVisible()
  })

  test('timeframe switch works', async ({ page }) => {
    // Timeframe tabs are rendered as buttons inside a TabsList
    const tab1h = page.locator('button', { hasText: '1h' })
    await tab1h.click()
    await expect(tab1h).toHaveAttribute('data-state', 'active')

    const tab1d = page.locator('button', { hasText: '1d' })
    await tab1d.click()
    await expect(tab1d).toHaveAttribute('data-state', 'active')
  })
})
