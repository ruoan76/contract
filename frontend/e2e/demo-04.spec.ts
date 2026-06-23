import { test, expect } from '@playwright/test'
import { expectToast, gotoRoute, switchRole, pickCreateMode, fillCreateStep1, goCreateStep2 } from './helpers'

const API = 'http://127.0.0.1:8000'

async function adminToken(request: import('@playwright/test').APIRequestContext) {
  const login = await request.post(`${API}/api/v1/system/login?username=admin&password=123456`)
  const token = (await login.json()).data?.token as string
  expect(token).toBeTruthy()
  return token
}

/** DEMO-04：拉黑相对方 → 创建合同被拒绝 */
test.describe('DEMO-04 黑名单拦截', () => {
  test('拉黑 → 创建拒绝', async ({ page, request }) => {
    test.setTimeout(90000)

    const token = await adminToken(request)
    const suffix = Date.now()
    const cpName = `E2E黑名单${suffix}`
    const created = await request.post(`${API}/api/v1/counterparties/`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: {
        name: cpName,
        credit_code: `91110000${String(suffix).slice(-8)}`,
      },
    })
    expect(created.ok()).toBeTruthy()
    const cpId = (await created.json()).data?.id as number
    expect(cpId).toBeGreaterThan(0)

    await page.goto('/')
    await switchRole(page, '系统管理员')
    await gotoRoute(page, '/counterparties', '相对方管理')

    const targetRow = page.locator('.el-table__body tr').filter({
      has: page.locator('td').nth(1).getByText(cpName, { exact: true }),
    })
    await expect(targetRow).toBeVisible({ timeout: 15000 })
    await targetRow.getByRole('button', { name: '拉黑' }).click()
    await expectToast(page, '已加入黑名单')

    await switchRole(page, '起草人')
    const cpResp = page.waitForResponse(
      (r) => r.url().includes('/api/v1/counterparties') && r.status() === 200,
    )
    await gotoRoute(page, '/create', '新建合同')
    await cpResp

    await pickCreateMode(page, '空白起草')
    await fillCreateStep1(page, {
      title: '黑名单测试合同',
      counterparty: cpName,
      amount: 100000,
      exactOption: `${cpName}（黑名单）`,
    })
    await goCreateStep2(page)

    await page.getByRole('button', { name: '提交审批' }).click()
    const blockDialog = page.getByRole('dialog').filter({ hasText: '黑名单' })
    await expect(blockDialog).toBeVisible({ timeout: 10000 })
    await blockDialog.getByRole('button', { name: '知道了' }).click()
    await expectToast(page, /黑名单/)
  })
})
