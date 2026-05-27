import { test, expect } from '@playwright/test'
import { gotoRoute, switchRole } from './helpers'

/** 侧栏条款比对入口与选合同引导 */
test.describe('UX 条款比对导航', () => {
  test('侧栏进入条款比对引导页', async ({ page }) => {
    await page.goto('/')
    await switchRole(page, '法务专员')
    await page.getByRole('menuitem', { name: '条款比对' }).click()
    await expect(page.locator('.app-main h2')).toHaveText('条款比对')
    await expect(page.getByText('请选择要比对的合同')).toBeVisible()
    await expect(page.getByTestId('clause-compare-go')).toBeVisible()
  })
})
