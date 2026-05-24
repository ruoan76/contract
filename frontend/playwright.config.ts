import { defineConfig, devices } from '@playwright/test'

/** CI 由 workflow 预先启动 dev server，避免 webServer 双启动超时 */
const useExternalServer = !!process.env.CI

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: 'http://127.0.0.1:8080',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  ...(useExternalServer
    ? {}
    : {
        webServer: {
          command: 'npm run dev',
          url: 'http://127.0.0.1:8080',
          reuseExistingServer: true,
          timeout: 120000,
        },
      }),
})
