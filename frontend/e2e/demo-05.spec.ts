import { test, expect } from '@playwright/test'

/** DEMO-05：评审退回 → 修订 */
test.describe('DEMO-05 退回修订', () => {
  test('法务退回 → 修订提交', async ({ page }) => {
    await page.goto('/')

    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '起草人' }).click()
    await page.getByRole('menuitem', { name: '新建合同' }).click()
    await page.getByRole('button', { name: '提交审批' }).click()
    await expect(page.getByText(/合同 #\d+ 已提交审批/)).toBeVisible({ timeout: 15000 })

    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '部门主管' }).click()
    await page.getByRole('menuitem', { name: '待办审批' }).click()
    await page.getByRole('button', { name: '通过' }).first().click()
    await expect(page.getByText('审批通过')).toBeVisible({ timeout: 10000 })

    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '法务专员' }).click()
    await page.getByRole('menuitem', { name: '评审工作台' }).click()
    const returnBtn = page.getByRole('button', { name: '退回修订' })
    if (await returnBtn.isVisible().catch(() => false)) {
      await returnBtn.click()
      await expect(page.getByText(/退回|修订/)).toBeVisible({ timeout: 10000 })
    }

    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '起草人' }).click()
    await page.getByRole('menuitem', { name: '合同列表' }).click()
    await page.getByRole('button', { name: '详情' }).first().click()
    const revisionLink = page.getByRole('button', { name: '修订' })
    if (await revisionLink.isVisible().catch(() => false)) {
      await revisionLink.click()
      await page.locator('textarea').first().fill('修订后的合同正文内容')
      await page.getByRole('button', { name: '提交修订' }).click()
      await expect(page.getByText(/修订|成功/)).toBeVisible({ timeout: 10000 })
    }
  })
})
