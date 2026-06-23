import { test, expect } from '@playwright/test'
import { gotoRoute, switchRole, pickCreateMode, expectToast } from './helpers'

/** OCR 低置信度时须勾选确认才可提交 */
test.describe('UX OCR 提交确认', () => {
  test('低置信度解析须勾选确认', async ({ page }) => {
    test.setTimeout(60000)
    await page.goto('/')
    await switchRole(page, '起草人')
    await gotoRoute(page, '/create', '新建合同')

    await page.route('**/api/v1/contracts/parse', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200,
          data: {
            filename: 'mock.pdf',
            ocr_used: true,
            char_count: 1200,
            fields: {
              title: 'OCR 测试合同',
              party_a: '甲方公司',
              party_b: '得力集团',
              amount: 100000,
              full_text: '测试正文',
              confidence: 0.45,
              party_parse_warning: true,
              contract_type: 'purchase',
            },
          },
        }),
      })
    })

    await pickCreateMode(page, '智能起草')

    const buffer = Buffer.from('%PDF-1.4 mock')
    await page.locator('[data-testid="ai-parse-upload"] input[type="file"]').setInputFiles({
      name: 'mock-scan.pdf',
      mimeType: 'application/pdf',
      buffer,
    })

    await expectToast(page, /解析完成/)
    await expect(
      page.locator('.el-form-item').filter({ hasText: '合同标题' }).locator('input'),
    ).toHaveValue('OCR 测试合同', { timeout: 15000 })

    await page.getByRole('button', { name: '下一步' }).click()
    await expect(page.getByTestId('ocr-confirm-checkbox')).toBeVisible({ timeout: 15000 })

    await page.getByRole('button', { name: '提交审批' }).click()
    await expect(page.locator('.el-message').filter({ hasText: /请先勾选/ })).toBeVisible({
      timeout: 10000,
    })

    await page.getByTestId('ocr-confirm-checkbox').click()
    await page.getByRole('button', { name: '提交审批' }).click()
    await expect(page.getByRole('dialog').filter({ hasText: 'OCR 字段确认' })).toBeVisible({
      timeout: 10000,
    })
  })
})
