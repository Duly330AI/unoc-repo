import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    pool: 'threads',
    poolOptions: { threads: { minThreads: 1, maxThreads: 1 } },
    passWithNoTests: false,
    setupFiles: ['./vitest.setup.ts'],
    coverage: { enabled: false, reporter: ['text'] },
    exclude: ['**/node_modules/**', '**/dist/**', 'tests-e2e/**']
  }
})
