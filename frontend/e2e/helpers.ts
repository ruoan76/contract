import { expect, type Page } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:8000'

const ROLE_LABEL_TO_KEY: Record<string, string> = {
  起草人: 'drafter',
  部门主管: 'approver',
  法务专员: 'legal',
  财务专员: 'finance',
  高管: 'executive',
  档案管理员: 'archivist',
  系统管理员: 'admin',
}

const ROLE_KEY_TO_USER: Record<string, string> = {
  drafter: 'drafter1',
  approver: 'approver1',
  legal: 'legal1',
  finance: 'finance1',
  executive: 'executive1',
  admin: 'admin',
  archivist: 'admin',
}

/** 关闭新建合同后的「流程匹配」弹窗 */
export async function dismissFlowDialog(page: Page) {
  const dialog = page.getByRole('dialog', { name: '流程匹配' })
  if (await dialog.isVisible({ timeout: 3000 }).catch(() => false)) {
    await dialog.getByRole('button', { name: '关闭', exact: true }).click()
    await dialog.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
  }
}

/** 通过 API 登录切换用户（不依赖 UI 演示角色） */
export async function switchRole(page: Page, roleLabel: string) {
  const roleKey = ROLE_LABEL_TO_KEY[roleLabel]
  const username = ROLE_KEY_TO_USER[roleKey]
  if (!username) throw new Error(`未知角色标签: ${roleLabel}`)

  const res = await page.request.post(
    `${API_BASE}/api/v1/system/login?username=${username}&password=123456`,
  )
  const json = await res.json()
  expect(res.ok(), `登录失败 ${roleLabel}: ${JSON.stringify(json)}`).toBeTruthy()
  const token = json.data?.token as string
  const user = json.data?.user
  expect(token).toBeTruthy()

  await page.evaluate(
    ({ token, user, roleKey }) => {
      sessionStorage.setItem('api_token', token)
      sessionStorage.setItem('api_current_user', JSON.stringify(user))
      sessionStorage.setItem('app_role', roleKey)
    },
    { token, user, roleKey },
  )
  await page.reload()
  await page.waitForLoadState('networkidle').catch(() => {})
  await expect(page.locator('.user-menu-role')).toHaveText(roleLabel, { timeout: 15000 })
}

/** 直接跳转路由 */
export async function gotoRoute(page: Page, path: string, heading?: string) {
  await page.goto(path)
  await page.waitForLoadState('networkidle').catch(() => {})
  if (heading) {
    await expect(page.locator('.header-title').filter({ hasText: heading })).toBeVisible({
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

/** 选择新建向导的起草方式 */
export async function pickCreateMode(page: Page, modeTitle: string) {
  const card = page.locator('.mode-card').filter({ hasText: modeTitle })
  if (await card.isVisible({ timeout: 3000 }).catch(() => false)) {
    await card.click()
  }
}

/** 填写新建向导第一步 */
export async function fillCreateStep1(
  page: Page,
  data: { title: string; counterparty: string; amount: number; exactOption?: string },
) {
  await page.locator('.el-form-item').filter({ hasText: '合同标题' }).locator('input').fill(data.title)
  const cpForm = page.locator('.el-form-item').filter({ hasText: '相对方' })
  await cpForm.locator('.el-select').click()
  await cpForm.locator('input').fill(data.counterparty)
  const optionName = data.exactOption ?? data.counterparty
  await page.getByRole('option', { name: optionName }).click({ timeout: 15000 })
  const amountInput = page.locator('.el-form-item').filter({ hasText: '金额' }).locator('input').first()
  await amountInput.fill(String(data.amount))
}

/** 进入新建向导正文步骤 */
export async function goCreateStep2(page: Page) {
  await page.getByRole('button', { name: '下一步' }).click()
  await page.locator('.el-form-item').filter({ hasText: '合同正文' }).locator('textarea').waitFor({
    timeout: 10000,
  })
}

/** 完成新建向导并填写默认测试数据 */
export async function completeCreateWizard(
  page: Page,
  opts?: { title?: string; amount?: number; counterparty?: string; exactOption?: string; mode?: string },
) {
  await pickCreateMode(page, opts?.mode ?? '空白起草')
  await fillCreateStep1(page, {
    title: opts?.title ?? 'E2E 测试采购合同',
    counterparty: opts?.counterparty ?? '得力集团',
    amount: opts?.amount ?? 80000,
    exactOption: opts?.exactOption,
  })
  await goCreateStep2(page)
  await page.locator('.el-form-item').filter({ hasText: '合同正文' }).locator('textarea').fill('E2E 测试合同正文')
}

/** 提交审批并返回新建合同 ID */
export async function submitContract(
  page: Page,
  opts?: { title?: string; amount?: number; counterparty?: string; exactOption?: string; mode?: string },
): Promise<number> {
  await completeCreateWizard(page, opts)
  await page.getByRole('button', { name: '提交审批' }).click()
  const toast = page.locator('.el-message').filter({ hasText: /已提交审批/ })
  await expect(toast).toBeVisible({ timeout: 15000 })
  const text = await toast.innerText()
  const match = text.match(/#(\d+)/)
  return match ? Number(match[1]) : 0
}

/** 待办表格中按合同 ID 精确匹配行 */
function pendingRow(page: Page, contractId: number) {
  return page
    .locator('.el-table__body')
    .first()
    .locator('tr')
    .filter({
      has: page.getByRole('cell', { name: String(contractId), exact: true }),
    })
}

/** 待办审批：填写意见并通过 */
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
  for (const role of roles) {
    await switchRole(page, role)
    await gotoRoute(page, `/review-workspace/${contractId}`, '评审工作台')
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
