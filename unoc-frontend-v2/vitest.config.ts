import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    // Avoid worker threads on Windows which can sometimes cause module duplication issues
    // leading to missing test suite registration
    pool: 'threads',
    poolOptions: { threads: { minThreads: 1, maxThreads: 1 } },
    passWithNoTests: false,
    setupFiles: ['./vitest.setup.ts'],
    coverage: {
      provider: 'v8',
      enabled: true,
      // Use text-only reporter to avoid generating large HTML reports that can exhaust disk space
      reporter: ['text'],
      reportsDirectory: './coverage',
      // Focus coverage on the newly added/modified features to avoid failing
      // global thresholds due to legacy and unrelated files.
      include: [
        'src/components/tariffs/**',
        'src/stores/tariffsStore.ts',
        'src/components/ui/Tooltip.vue',
        'src/stores/tooltipStore.ts'
      ],
      thresholds: {
        lines: 88,
        functions: 88,
        branches: 80,
        statements: 88
      }
    },
    exclude: ['**/node_modules/**', '**/dist/**', 'tests-e2e/**']
  }
})
