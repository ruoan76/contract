import { test, expect } from '@playwright/test'
import {
  approveFirstPending,
  dismissFlowDialog,
  expectToast,
  gotoRoute,
  submitContract,
  switchRole,
} from './helpers'

/** DEMO-05：评审退回 → 修订 */
test.describe('DEMO-05 退回修订', () => {
  test('法务退回 → 修订提交', async ({ page }) => {
    test.setTimeout(120000)
    await page.goto('/')

    await switchRole(page, '起草人')
    await gotoRoute(page, '/create', '新建合同')
    const contractId = await submitContract(page)
    expect(contractId).toBeGreaterThan(0)
    await dismissFlowDialog(page)

    await switchRole(page, '部门主管')
    await gotoRoute(page, '/approvals', '待办审批')
    await approveFirstPending(page, contractId)
    await expectToast(page, '审批通过')

    await switchRole(page, '法务专员')
    await gotoRoute(page, `/review-workspace/${contractId}`, '评审工作台')
    await page.getByRole('button', { name: '退回修订' }).click()
    await expectToast(page, '已退回修订')

    await switchRole(page, '起草人')
    await gotoRoute(page, `/contracts/${contractId}/revision`, '修订工作台')
    await page.locator('textarea').first().fill('修订后的合同正文内容')
    await page.getByRole('button', { name: '提交修订' }).click()
    await expectToast(page, /修订/)
  })
})
