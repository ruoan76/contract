import { test, expect } from '@playwright/test'

/** 静态路由：逐页打开，收集 console.error 与 /api/ 4xx/5xx */
const STATIC_ROUTES = [
  '/',
  '/messages',
  '/create',
  '/contracts',
  '/templates',
  '/ai-review',
  '/review-center',
  '/review-workspace',
  '/review-history',
  '/approvals',
  '/seal',
  '/archives',
  '/counterparties',
  '/config',
  '/users',
  '/audit',
]

/** 已知可忽略的 API 失败（空上下文、占位数据等） */
function isAllowedApiFailure(url: string, status: number): boolean {
  if (status === 401) return true // skip-auth 切换角色时偶发
  // 仅忽略「合同本身不存在」的 404，不忽略 latest-review 等业务接口
  if (status === 404 && /\/api\/v1\/contracts\/\d+$/.test(url.split('?')[0] ?? '')) return true
  return false
}

function attachCollectors(page: import('@playwright/test').Page) {
  const consoleErrors: string[] = []
  const apiErrors: { url: string; status: number }[] = []

  page.on('console', (msg) => {
    if (msg.type() !== 'error') return
    const text = msg.text()
    // 忽略浏览器/扩展噪声
    if (text.includes('favicon') || text.includes('DevTools')) return
    consoleErrors.push(text)
  })

  page.on('response', (res) => {
    if (!res.url().includes('/api/')) return
    const status = res.status()
    if (status < 400) return
    if (isAllowedApiFailure(res.url(), status)) return
    apiErrors.push({ url: res.url(), status })
  })

  return { consoleErrors, apiErrors }
}

test.describe('路由冒烟：控制台与 API 错误', () => {
  test.setTimeout(60000)

  for (const route of STATIC_ROUTES) {
    test(`打开 ${route}`, async ({ page }) => {
      const { consoleErrors, apiErrors } = attachCollectors(page)
      await page.goto(route)
      await page.waitForLoadState('networkidle').catch(() => {})
      await page.waitForTimeout(800)

      expect(
        consoleErrors,
        `控制台 error @ ${route}:\n${consoleErrors.join('\n')}`,
      ).toEqual([])
      expect(
        apiErrors,
        `API 失败 @ ${route}:\n${apiErrors.map((e) => `${e.status} ${e.url}`).join('\n')}`,
      ).toEqual([])
    })
  }

  test('带合同 ID 的详情页', async ({ page, request }) => {
    const login = await request.post(
      'http://127.0.0.1:8000/api/v1/system/login?username=drafter1&password=123456',
    )
    const loginJson = await login.json()
    const token = loginJson.data?.token as string
    expect(token).toBeTruthy()

    const list = await request.get('http://127.0.0.1:8000/api/v1/contracts/?page=1&page_size=1', {
      headers: { Authorization: `Bearer ${token}` },
    })
    const listJson = await list.json()
    const id = listJson.data?.items?.[0]?.id as number | undefined
    test.skip(!id, '无合同数据，跳过详情页冒烟')

    const detailRoutes = [
      `/contracts/${id}`,
      `/contracts/${id}/approval-history`,
      `/ai-review/${id}`,
      `/contracts/${id}/clause-compare`,
    ]
    for (const route of detailRoutes) {
      const { consoleErrors, apiErrors } = attachCollectors(page)
      await page.goto(route)
      await page.waitForLoadState('networkidle').catch(() => {})
      await page.waitForTimeout(800)

      expect(consoleErrors, `控制台 error @ ${route}`).toEqual([])
      expect(apiErrors, `API 失败 @ ${route}`).toEqual([])
    }
  })

  test('无 AI 审查记录的合同：latest-review 不得 404', async ({ page, request }) => {
    const login = await request.post(
      'http://127.0.0.1:8000/api/v1/system/login?username=drafter1&password=123456',
    )
    const token = (await login.json()).data?.token as string
    expect(token).toBeTruthy()

    // 新建草稿且未触发 AI 审查
    const created = await request.post('http://127.0.0.1:8000/api/v1/contracts/', {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: {
        title: '冒烟-无AI审查',
        contract_type: 'purchase',
        counterparty_name: '得力集团',
        amount: 1000,
        content: '测试',
      },
    })
    const contractId = (await created.json()).data?.id as number
    expect(contractId).toBeGreaterThan(0)

    const latestReview404: string[] = []
    page.on('response', (res) => {
      if (
        res.url().includes(`/api/v1/ai-review/contracts/${contractId}/latest-review`) &&
        res.status() === 404
      ) {
        latestReview404.push(res.url())
      }
    })

    await page.goto(`/contracts/${contractId}`)
    await page.waitForLoadState('networkidle').catch(() => {})
    await page.waitForTimeout(500)

    expect(latestReview404, 'latest-review 不应返回 404').toEqual([])
  })

  test('合同详情页上传附件不得 500', async ({ page, request }) => {
    const login = await request.post(
      'http://127.0.0.1:8000/api/v1/system/login?username=drafter1&password=123456',
    )
    const token = (await login.json()).data?.token as string
    expect(token).toBeTruthy()

    const created = await request.post('http://127.0.0.1:8000/api/v1/contracts/', {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: {
        title: '冒烟-上传附件',
        contract_type: 'purchase',
        counterparty_name: '得力集团',
        amount: 1000,
        content: '测试上传',
      },
    })
    const contractId = (await created.json()).data?.id as number
    expect(contractId).toBeGreaterThan(0)

    const uploadFailures: string[] = []
    page.on('response', (res) => {
      if (res.url().includes(`/api/v1/contracts/${contractId}/upload`) && res.status() >= 500) {
        uploadFailures.push(`${res.status()} ${res.url()}`)
      }
    })

    await page.goto(`/contracts/${contractId}`)
    await page.waitForLoadState('networkidle').catch(() => {})
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'smoke-upload.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('smoke upload test'),
    })
    await page.waitForTimeout(1500)

    expect(uploadFailures, '上传接口不应 500').toEqual([])
  })
})
