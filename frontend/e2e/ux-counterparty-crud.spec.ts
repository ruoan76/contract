import { test, expect } from '@playwright/test'
import { expectToast, gotoRoute, switchRole } from './helpers'

test.describe('UX 相对方管理 CRUD', () => {
  test('搜索、新增、编辑、详情', async ({ page }) => {
    test.setTimeout(90000)
    const suffix = Date.now()
    const cpName = `E2E相对方${suffix}`
    const creditCode = `91110000${String(suffix).slice(-8)}`

    await page.goto('/')
    await switchRole(page, '系统管理员')
    await gotoRoute(page, '/counterparties', '相对方管理')

    await page.getByRole('button', { name: '新增相对方' }).click()
    const createDialog = page.getByRole('dialog', { name: '新增相对方' })
    await createDialog.getByPlaceholder('单位全称').fill(cpName)
    await createDialog.getByPlaceholder('统一社会信用代码（可选）').fill(creditCode)
    await createDialog.getByRole('button', { name: '创建' }).click()
    await expectToast(page, '相对方已创建')

    await page.getByPlaceholder('搜索名称/信用代码').fill(cpName)
    await page.getByRole('button', { name: '搜索' }).click()

    const row = page.locator('.el-table__body tr').filter({
      has: page.getByText(cpName, { exact: true }),
    })
    await expect(row).toBeVisible({ timeout: 15000 })

    await row.getByRole('button', { name: '详情' }).click()
    await expect(page.locator('.el-drawer').filter({ hasText: '相对方详情' })).toBeVisible()
    await expect(page.locator('.el-drawer').getByText(creditCode)).toBeVisible()
    await page.keyboard.press('Escape')

    await row.getByRole('button', { name: '编辑' }).click()
    const editDialog = page.getByRole('dialog', { name: '编辑相对方' })
    await editDialog.locator('label').filter({ hasText: '联系人' }).locator('..').locator('input').fill('测试联系人')
    await editDialog.getByRole('button', { name: '保存' }).click()
    await expectToast(page, '已保存')
  })
})
