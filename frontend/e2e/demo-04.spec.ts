import { test, expect } from '@playwright/test'

/** DEMO-04：拉黑相对方 → 创建合同被拒绝 */
test.describe('DEMO-04 黑名单拦截', () => {
  test('拉黑 → 创建拒绝', async ({ page }) => {
    await page.goto('/')

    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '系统管理员' }).click()
    await page.getByRole('menuitem', { name: '相对方管理' }).click()

    // 读取第一行相对方名称，拉黑后必须用同一名称创建合同
    const nameCell = page.locator('.el-table__body tr').first().locator('td').nth(1)
    const counterpartyName = (await nameCell.innerText()).trim()
    expect(counterpartyName.length).toBeGreaterThan(0)

    await page.getByRole('button', { name: '拉黑' }).first().click()
    await expect(page.getByText('已加入黑名单')).toBeVisible({ timeout: 10000 })

    await page.locator('.header-right .el-select').click()
    await page.getByRole('option', { name: '起草人' }).click()
    await page.getByRole('menuitem', { name: '新建合同' }).click()

    // 将相对方改为刚拉黑的企业
    const cpSelect = page.locator('.el-select').filter({ has: page.locator('input') }).last()
    await cpSelect.click()
    await page.getByRole('option', { name: counterpartyName }).click()

    await page.getByRole('button', { name: '提交审批' }).click()
    await expect(page.getByText(/黑名单|拒绝|403|不允许/)).toBeVisible({ timeout: 15000 })
  })
})
