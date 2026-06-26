import { test, expect } from '@playwright/test'
import { expectToast, gotoRoute, switchRole, pickCreateMode, fillCreateStep1, goCreateStep2 } from './helpers'

/** 新建合同选黑名单相对方时前端拦截（与 DEMO-04 同路径，断言 MessageBox） */
test.describe('UX 黑名单起草拦截', () => {
  test('选黑名单后提交被阻止', async ({ page, request }) => {
    test.setTimeout(90000)
    const API = 'http://127.0.0.1:8000'
    const suffix = Date.now()
    const cpName = `UX黑名单${suffix}`

    const login = await request.post(`${API}/api/v1/system/login?username=admin&password=admin123`)
    const token = (await login.json()).data?.token as string

    const created = await request.post(`${API}/api/v1/counterparties/`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: {
        name: cpName,
        credit_code: `91110000${String(suffix).slice(-8)}`,
      },
    })
    const cpId = (await created.json()).data?.id as number
    expect(cpId).toBeGreaterThan(0)

    await page.goto('/')
    await switchRole(page, '系统管理员')
    await gotoRoute(page, '/counterparties', '相对方管理')

    const targetRow = page.locator('.el-table__body tr').filter({
      has: page.locator('td').nth(1).getByText(cpName, { exact: true }),
    })
    await page.getByPlaceholder('搜索名称/信用代码').fill(cpName)
    await page.getByRole('button', { name: '搜索' }).click()
    await expect(targetRow).toBeVisible({ timeout: 15000 })
    await targetRow.getByRole('button', { name: '拉黑' }).click()
    const blDialog = page.getByRole('dialog').filter({ hasText: '确认拉黑' })
    await blDialog.locator('input').fill('E2E测试拉黑')
    await blDialog.getByRole('button', { name: '确定' }).click()
    await expectToast(page, '已加入黑名单')

    await switchRole(page, '起草人')
    const cpResp = page.waitForResponse(
      (r) => r.url().includes('/api/v1/counterparties') && r.status() === 200,
    )
    await gotoRoute(page, '/create', '新建合同')
    await cpResp

    await pickCreateMode(page, '空白起草')
    await fillCreateStep1(page, {
      title: '黑名单拦截测试',
      counterparty: cpName,
      amount: 100000,
      exactOption: `${cpName}（黑名单）`,
    })
    await goCreateStep2(page)

    await page.getByRole('button', { name: '提交审批' }).click()
    const blockDialog = page.getByRole('dialog').filter({ hasText: '黑名单拦截' })
    await expect(blockDialog).toBeVisible({ timeout: 10000 })
    await blockDialog.getByRole('button', { name: '知道了' }).click()
    await expectToast(page, /黑名单/)
  })
})
