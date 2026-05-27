import { expect, type Page } from '@playwright/test'

/** 关闭新建合同后的「流程匹配」弹窗 */
export async function dismissFlowDialog(page: Page) {
  const dialog = page.getByRole('dialog', { name: '流程匹配' })
  if (await dialog.isVisible({ timeout: 3000 }).catch(() => false)) {
    await dialog.getByRole('button', { name: '关闭', exact: true }).click()
    await dialog.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
  }
}

/** 切换演示角色并等待侧栏角色更新 */
export async function switchRole(page: Page, roleLabel: string) {
  const roleBadge = page.locator('.sidebar .user-role')
  if ((await roleBadge.innerText()) === roleLabel) return
  await page.locator('.header-right .el-select').click()
  await page.getByRole('option', { name: roleLabel, exact: true }).click()
  await expect(roleBadge).toHaveText(roleLabel, { timeout: 15000 })
  await page.waitForLoadState('networkidle').catch(() => {})
}

/** 直接跳转路由（比侧栏 menuitem 更稳定） */
export async function gotoRoute(page: Page, path: string, heading?: string) {
  await page.goto(path)
  await page.waitForLoadState('networkidle').catch(() => {})
  if (heading) {
    await expect(page.locator('.app-main h2').filter({ hasText: heading })).toBeVisible({
      timeout: 20000,
    })
  }
}

/** 等待 Element Plus 全局消息 */
export async function expectToast(page: Page, text: string | RegExp) {
  await expect(page.locator('.el-message').filter({ hasText: text }).first()).toBeVisible({
    timeout: 15000,
  })
}

/** 提交审批并返回新建合同 ID */
export async function submitContract(page: Page): Promise<number> {
  await page.getByRole('button', { name: '提交审批' }).click()
  const toast = page.locator('.el-message').filter({ hasText: /已提交审批/ })
  await expect(toast).toBeVisible({ timeout: 15000 })
  const text = await toast.innerText()
  const match = text.match(/#(\d+)/)
  return match ? Number(match[1]) : 0
}

/** 待办表格中按合同 ID 精确匹配行（避免 hasText 子串误匹配） */
function pendingRow(page: Page, contractId: number) {
  return page
    .locator('.el-table__body')
    .first()
    .locator('tr')
    .filter({
      has: page.getByRole('cell', { name: String(contractId), exact: true }),
    })
}

/** 待办审批：填写意见并通过（可按合同 ID 过滤） */
export async function approveFirstPending(page: Page, contractId?: number) {
  await page.locator('.el-loading-mask').waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {})
  const row =
    contractId != null && contractId > 0
      ? pendingRow(page, contractId)
      : page.locator('.el-table__body').first().locator('tr').first()
  await expect(row).toBeVisible({ timeout: 15000 })
  const approveBtn = row.getByRole('button', { name: '通过' }).first()
  await approveBtn.click()
  const box = page.getByRole('dialog')
  await expect(box).toBeVisible({ timeout: 5000 })
  const input = box.locator('input').first()
  await input.fill('同意')
  const approveResp = page.waitForResponse(
    (r) => r.url().includes('/api/v1/approvals/') && r.url().includes('/approve') && r.request().method() === 'POST',
  )
  await box.getByRole('button', { name: '通过' }).click()
  const resp = await approveResp
  expect(resp.status(), `审批 API 失败: ${resp.status()}`).toBeLessThan(400)
}

/** 多轮切换角色直至指定合同待办审批清空或达到上限 */
export async function completeApprovalChain(
  page: Page,
  roles: string[],
  contractId?: number,
  maxRounds = 8,
) {
  for (let round = 0; round < maxRounds; round++) {
    let acted = false
    for (const role of roles) {
      await switchRole(page, role)
      await gotoRoute(page, '/approvals', '待办审批')
      await page.locator('.el-loading-mask').waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {})
      const row =
        contractId != null && contractId > 0
          ? pendingRow(page, contractId)
          : page.locator('.el-table__body').first().locator('tr').first()
      const approveBtn = row.getByRole('button', { name: '通过' }).first()
      if (await approveBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await approveFirstPending(page, contractId)
        await expectToast(page, '审批通过')
        acted = true
      }
    }
    if (!acted) break
  }
}

export async function approveReviewRoles(page: Page, contractId: number, roles: string[]) {
  const roleToTab: Record<string, string> = {
    法务专员: '法务',
    财务专员: '财务',
    高管: '高管',
  }
  for (const role of roles) {
    await switchRole(page, role)
    await gotoRoute(page, `/review-workspace/${contractId}`, '评审工作台')
    const tabName = roleToTab[role]
    if (tabName) {
      await page.getByRole('tab', { name: tabName }).click()
    }
    const btn = page.getByRole('button', { name: '提交通过' })
    if (await btn.isVisible().catch(() => false)) {
      await expect(btn).toBeEnabled({ timeout: 15000 })
      await btn.click()
      await expect(
        page.locator('.el-message').filter({
          hasText: /评审已通过|该角色已评审|仅审批通过后|提交失败|请先/,
        }),
      ).toBeVisible({ timeout: 15000 })
    }
  }
}
