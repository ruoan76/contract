import { test, expect } from '@playwright/test'

/** DEMO-03：修改阈值 → 大额合同 → 审批历史 */
test.describe('DEMO-03 大额流程', () => {
  test('阈值配置 → 大额合同 → 审批历史', async ({ page }) => {
    await page.goto('/')

    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '系统管理员' }).click()
    await page.getByRole('menuitem', { name: '审批配置' }).click()
    await page.getByRole('button', { name: '保存阈值' }).click()
    await expect(page.getByText('阈值已保存')).toBeVisible({ timeout: 10000 })

    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '起草人' }).click()
    await page.getByRole('menuitem', { name: '新建合同' }).click()
    await page.locator('.el-input-number input').fill('2500000')
    await page.getByRole('button', { name: '提交审批' }).click()
    await expect(page.getByText(/合同 #\d+ 已提交审批/)).toBeVisible({ timeout: 15000 })

    await page.getByRole('menuitem', { name: '合同列表' }).click()
    await page.getByRole('button', { name: '详情' }).first().click()
    await page.getByRole('button', { name: '审批历史' }).click()
    await expect(page.getByText(/审批历史|流程/)).toBeVisible({ timeout: 10000 })
  })
})
