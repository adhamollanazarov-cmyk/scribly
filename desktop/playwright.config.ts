import { defineConfig } from '@playwright/test'

// Electron smoke test: one app at a time (global shortcut, single tray).
export default defineConfig({
  testDir: './e2e',
  workers: 1,
  timeout: 90_000,
  reporter: 'list',
  use: { trace: 'retain-on-failure' },
})
