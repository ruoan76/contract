import { test, expect } from '@playwright/test'

/**
 * DEMO-01 E2E：需 backend :8000 运行且已 seed（密码 123456）
 * 运行：cd frontend && npx playwright test
 */
test.describe('DEMO-01 简易流程', () => {
  test('起草 → 审批 → 法务评审 → 用印', async ({ page }) => {
    await page.goto('/')

    // 起草人新建
    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '起草人' }).click()
    await page.getByRole('button', { name: '新建合同' }).click()
    await page.getByRole('button', { name: '提交审批' }).click()
    await expect(page.getByText('已提交审批').or(page.getByText('合同 #'))).toBeVisible({ timeout: 15000 })

    // 部门主管审批
    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '部门主管' }).click()
    await page.getByRole('menuitem', { name: '待办审批' }).click()
    await page.getByRole('button', { name: '通过' }).first().click()
    await expect(page.getByText('审批通过')).toBeVisible({ timeout: 10000 })

    // 法务评审
    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '法务专员' }).click()
    await page.getByRole('menuitem', { name: '评审工作台' }).click()
    await page.getByRole('button', { name: '提交通过' }).click()
    await expect(page.getByText('评审已通过').or(page.getByText('法务'))).toBeVisible({ timeout: 10000 })

    // 用印
    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '起草人' }).click()
    await page.getByRole('menuitem', { name: '用印管理' }).click()
    await page.getByRole('button', { name: /申请用印/ }).click()
    await expect(page.getByText('用印申请已提交')).toBeVisible({ timeout: 10000 })

    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '系统管理员' }).click()
    await page.getByRole('button', { name: '确认用印' }).first().click()
    await expect(page.getByText('用印已确认')).toBeVisible({ timeout: 10000 })
  })
})
