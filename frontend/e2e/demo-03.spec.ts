import { test, expect } from '@playwright/test'
import { dismissFlowDialog, gotoRoute, submitContract, switchRole } from './helpers'

/** DEMO-03：修改阈值 → 大额合同 → 审批历史 */
test.describe('DEMO-03 大额流程', () => {
  test('阈值配置 → 大额合同 → 审批历史', async ({ page }) => {
    test.setTimeout(90000)
    await page.goto('/')

    await switchRole(page, '系统管理员')
    await gotoRoute(page, '/config', '审批配置')
    await page.locator('.el-loading-mask').waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {})
    await page.getByRole('button', { name: '保存阈值' }).click()
    await expect(page.getByText('阈值已保存')).toBeVisible({ timeout: 10000 })

    await switchRole(page, '起草人')
    await gotoRoute(page, '/create', '新建合同')
    const contractId = await submitContract(page, { amount: 2500000 })
    expect(contractId).toBeGreaterThan(0)
    await dismissFlowDialog(page)

    await gotoRoute(page, `/contracts/${contractId}/approval-history`, '审批历史')
  })
})
