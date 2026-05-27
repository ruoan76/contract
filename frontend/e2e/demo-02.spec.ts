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

/** DEMO-02：标准流程审批链 → 三角色评审（MLX 实机审查见集成测 / 手工演示） */
test.describe('DEMO-02 标准流程', () => {
  test('起草 → 审批链 → 法务/财务/高管评审', async ({ page }) => {
    test.setTimeout(120000)
    await page.goto('/')

    await switchRole(page, '起草人')
    await gotoRoute(page, '/create', '新建合同')
    await page.locator('.el-input-number input').fill('320000')
    const contractId = await submitContract(page)
    expect(contractId).toBeGreaterThan(0)
    await dismissFlowDialog(page)

    await completeApprovalChain(page, ['部门主管'], contractId)

    // E2E 不测 MLX 实机（分钟级）；审批链 + 三角色评审覆盖 DEMO-02 主线
    await approveReviewRoles(page, contractId, ['法务专员', '财务专员', '高管'])
  })
})
