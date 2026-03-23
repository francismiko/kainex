import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('stats cards are visible', async ({ page }) => {
    const cards = ['总资产', '今日收益', '活跃策略', '风险敞口']
    for (const title of cards) {
      await expect(page.locator('text=' + title).first()).toBeVisible()
    }
  })

  test('strategy status table is visible', async ({ page }) => {
    await expect(page.locator('text=策略实时状态').first()).toBeVisible()
    // Table should have header columns
    await expect(page.locator('th', { hasText: '策略' }).first()).toBeVisible()
    await expect(page.locator('th', { hasText: '状态' }).first()).toBeVisible()
    await expect(page.locator('th', { hasText: '收益' }).first()).toBeVisible()
  })

  test('PnL chart renders', async ({ page }) => {
    await expect(page.locator('text=收益曲线').first()).toBeVisible()
    // The PnL chart is a lazy-loaded echarts component; wait for its container
    const chartCard = page.locator('text=收益曲线').locator('..')
    await expect(chartCard).toBeVisible()
  })
})
