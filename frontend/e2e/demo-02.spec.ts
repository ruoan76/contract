import { test, expect } from '@playwright/test'
import {
  approveReviewRoles,
  completeApprovalChain,
  dismissFlowDialog,
  expectToast,
  gotoRoute,
  submitContract,
  switchRole,
} from './helpers'

/** DEMO-02：标准流程 AI → 三角色评审（归档在 Archives 页） */
test.describe('DEMO-02 标准流程', () => {
  test('起草 → 审批链 → AI → 法务评审', async ({ page }) => {
    test.setTimeout(120000)
    await page.goto('/')

    await switchRole(page, '起草人')
    await gotoRoute(page, '/create', '新建合同')
    await page.locator('.el-input-number input').fill('320000')
    const contractId = await submitContract(page)
    expect(contractId).toBeGreaterThan(0)
    await dismissFlowDialog(page)

    await completeApprovalChain(page, ['部门主管'], contractId)

    await switchRole(page, '法务专员')
    await gotoRoute(page, `/ai-review/${contractId}`, '审查报告')
    await page.getByRole('button', { name: '触发审查' }).click()
    await expectToast(page, 'AI 审查已完成')

    await approveReviewRoles(page, contractId, ['法务专员', '财务专员', '高管'])
  })
})
