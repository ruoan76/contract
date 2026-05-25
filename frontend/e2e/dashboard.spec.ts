import { test, expect } from '@playwright/test'

test.describe('Dashboard 冒烟', () => {
  test('看板统计与三栏加载', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('.stat-label').filter({ hasText: '合同总数' })).toBeVisible({
      timeout: 10000,
    })
    await expect(page.locator('.stat-label').filter({ hasText: '待审批' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '执行中' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '即将到期' })).toBeVisible()
    await expect(page.locator('.kanban-title').first()).toBeVisible()
  })
})
