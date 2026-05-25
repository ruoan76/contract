import { test, expect } from '@playwright/test'
import { expectToast, gotoRoute, switchRole } from './helpers'

/** DEMO-04：拉黑相对方 → 创建合同被拒绝 */
test.describe('DEMO-04 黑名单拦截', () => {
  test('拉黑 → 创建拒绝', async ({ page }) => {
    test.setTimeout(90000)
    await page.goto('/')

    await switchRole(page, '系统管理员')
    await gotoRoute(page, '/counterparties', '相对方管理')

    const targetRow = page
      .locator('.el-table__body tr')
      .filter({ hasNot: page.locator('td').filter({ hasText: '得力集团' }) })
      .first()
    const nameCell = targetRow.locator('td').nth(1)
    await expect(nameCell).toBeVisible({ timeout: 15000 })
    const counterpartyName = (await nameCell.innerText()).trim()
    expect(counterpartyName.length).toBeGreaterThan(0)

    await targetRow.getByRole('button', { name: '拉黑' }).click()
    await expectToast(page, '已加入黑名单')

    await switchRole(page, '起草人')
    await gotoRoute(page, '/create', '新建合同')

    const cpSelect = page.locator('.el-form-item').filter({ hasText: '相对方' }).locator('.el-select')
    await cpSelect.click()
    await page.getByRole('option', { name: counterpartyName }).click()

    await page.getByRole('button', { name: '提交审批' }).click()
    await expectToast(page, /黑名单/)
  })
})
