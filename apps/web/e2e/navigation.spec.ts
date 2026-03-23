import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {
  test('homepage loads with correct title', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/Kainex/)
    await expect(page.locator('h1')).toHaveText('总览')
  })

  const pages = [
    { label: '策略管理', path: '/strategies', heading: '策略管理' },
    { label: '行情中心', path: '/market', heading: '行情中心' },
    { label: '交易记录', path: '/trades', heading: '交易记录' },
    { label: '持仓组合', path: '/portfolio', heading: '持仓组合' },
    { label: '风控监控', path: '/risk', heading: '风控监控' },
    { label: '价格告警', path: '/alerts', heading: '价格告警' },
    { label: '运行日志', path: '/logs', heading: '运行日志' },
    { label: '数据管理', path: '/data', heading: '数据管理' },
  ] as const

  for (const { label, path, heading } of pages) {
    test(`sidebar navigates to ${label}`, async ({ page }) => {
      await page.goto('/')
      // Click the sidebar link by its text
      await page.locator('aside a', { hasText: label }).click()
      await expect(page).toHaveURL(new RegExp(path))
      await expect(page.locator('h1')).toHaveText(heading)
    })
  }

  test('sidebar navigates to 设置', async ({ page }) => {
    await page.goto('/')
    await page.locator('aside a', { hasText: '设置' }).click()
    await expect(page).toHaveURL(/\/settings/)
    await expect(page.locator('h1')).toHaveText('设置')
  })
})
