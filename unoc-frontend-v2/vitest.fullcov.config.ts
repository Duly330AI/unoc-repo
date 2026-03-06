import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    pool: 'threads',
    poolOptions: { threads: { minThreads: 1, maxThreads: 1 } },
    passWithNoTests: false,
    setupFiles: ['./vitest.setup.ts'],
    includeSource: ['src/**/*.{ts,tsx,vue}'],
    coverage: {
      provider: 'v8',
      enabled: true,
      all: true,
      // Full project coverage
      include: ['src/**'],
      reporter: ['text', 'html', 'json-summary', 'lcov'],
      reportsDirectory: './coverage/full'
      // Intentionally no global thresholds for full report to avoid failing the run
    },
    exclude: ['**/node_modules/**', '**/dist/**', 'tests-e2e/**']
  }
})
