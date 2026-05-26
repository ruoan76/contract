import { test, expect } from '@playwright/test'
import { approveFirstPending, dismissFlowDialog, expectToast, gotoRoute, submitContract, switchRole } from './helpers'

/**
 * DEMO-01 E2E：需 backend :8000 运行且已 seed（密码 123456）
 * 运行：cd frontend && npx playwright test
 */
test.describe('DEMO-01 简易流程', () => {
  test('起草 → 审批 → 法务评审 → 用印', async ({ page }) => {
    test.setTimeout(90000)
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
    await page.getByRole('button', { name: '提交通过' }).click()
    await expectToast(page, /评审已通过|该角色已评审/)

    await switchRole(page, '起草人')
    await gotoRoute(page, '/seal', '用印管理')
    await page.getByRole('button', { name: /申请用印/ }).click()
    await expect(page.getByText('用印申请已提交')).toBeVisible({ timeout: 10000 })

    await switchRole(page, '系统管理员')
    await gotoRoute(page, '/seal', '用印管理')
    await page.getByRole('button', { name: '确认用印' }).first().click()
    await expect(page.getByText('用印已确认')).toBeVisible({ timeout: 10000 })
  })
})
