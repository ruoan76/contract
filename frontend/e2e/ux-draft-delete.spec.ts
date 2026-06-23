import { test, expect } from '@playwright/test'
import { expectToast, gotoRoute, switchRole } from './helpers'

const API_BASE = 'http://127.0.0.1:8000'

/** 通过 API 创建草稿（不提交审批） */
async function createDraftContract(
  page: import('@playwright/test').Page,
  title: string,
): Promise<number> {
  const token = await page.evaluate(() => sessionStorage.getItem('api_token'))
  expect(token).toBeTruthy()

  const res = await page.request.post(`${API_BASE}/api/v1/contracts/`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    data: {
      title,
      contract_type: 'service',
      counterparty_name: '得力集团',
      amount: 50000,
      content: 'E2E 草稿删除测试正文',
    },
  })
  const json = await res.json()
  expect(res.ok(), `创建草稿失败: ${JSON.stringify(json)}`).toBeTruthy()
  const id = json.data?.id as number
  expect(id).toBeGreaterThan(0)
  return id
}

test.describe('草稿合同主动删除', () => {
  test('详情页删除草稿后列表不再展示', async ({ page }) => {
    test.setTimeout(60000)
    const title = `E2E-草稿删除-${Date.now()}`

    await page.goto('/')
    await switchRole(page, '起草人')

    const contractId = await createDraftContract(page, title)

    await gotoRoute(page, `/contracts/${contractId}`, '合同详情')
    await page.getByRole('button', { name: '删除草稿' }).click()
    await page.getByRole('dialog', { name: '确认删除草稿？' }).getByRole('button', { name: '删除' }).click()
    await expectToast(page, '草稿已删除')

    await gotoRoute(page, '/contracts', '合同列表')
    await page.getByPlaceholder('搜索标题/相对方').fill(title)
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.locator('.el-table__body').getByText(title)).toHaveCount(0, {
      timeout: 10000,
    })
  })

  test('列表页删除草稿', async ({ page }) => {
    test.setTimeout(60000)
    const title = `E2E-列表删除-${Date.now()}`

    await page.goto('/')
    await switchRole(page, '起草人')

    const contractId = await createDraftContract(page, title)

    await gotoRoute(page, '/contracts', '合同列表')
    await page.getByPlaceholder('搜索标题/相对方').fill(title)
    await page.getByRole('button', { name: '查询' }).click()

    const row = page.locator('.el-table__body tr').filter({ hasText: title })
    await expect(row).toBeVisible({ timeout: 10000 })
    await row.getByRole('button', { name: '删除' }).click()
    await page.getByRole('dialog', { name: '确认删除草稿？' }).getByRole('button', { name: '删除' }).click()
    await expectToast(page, '草稿已删除')

    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.locator('.el-table__body').getByText(title)).toHaveCount(0, {
      timeout: 10000,
    })
    await expect(page.locator('.el-table__body').getByText(String(contractId))).toHaveCount(0)
  })
})
