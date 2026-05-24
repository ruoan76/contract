import { test, expect } from '@playwright/test'

/** DEMO-02：标准流程 AI → 三角色评审（归档在 Archives 页） */
test.describe('DEMO-02 标准流程', () => {
  test('起草 → 审批链 → AI → 法务评审', async ({ page }) => {
    await page.goto('/')

    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '起草人' }).click()
    await page.getByRole('menuitem', { name: '新建合同' }).click()
    await page.locator('.el-input-number input').fill('320000')
    await page.getByRole('button', { name: '提交审批' }).click()
    await expect(page.getByText(/合同 #\d+ 已提交审批/)).toBeVisible({ timeout: 15000 })

    for (const role of ['部门主管', '法务专员', '财务专员', '高管']) {
      await page.locator('.header-right .el-select').click()
      await page.getByRole('option', { name: role }).click()
      await page.getByRole('menuitem', { name: '待办审批' }).click()
      const approveBtn = page.getByRole('button', { name: '通过' }).first()
      if (await approveBtn.isVisible().catch(() => false)) {
        await approveBtn.click()
        await expect(page.getByText('审批通过')).toBeVisible({ timeout: 10000 })
      }
    }

    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '法务专员' }).click()
    await page.getByRole('menuitem', { name: '审查报告' }).click()
    await page.getByRole('button', { name: '触发审查' }).click()
    await expect(page.getByText(/审查已完成|风险/)).toBeVisible({ timeout: 15000 })

    await page.getByRole('menuitem', { name: '评审工作台' }).click()
    await page.getByRole('button', { name: '提交通过' }).click()
    await expect(page.getByText(/评审已通过|法务/)).toBeVisible({ timeout: 10000 })
  })
})
