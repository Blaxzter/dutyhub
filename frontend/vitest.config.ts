import vue from '@vitejs/plugin-vue'
import { URL, fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

/**
 * Standalone config — deliberately NOT `mergeConfig(viteConfig, …)`.
 *
 * `vite.config.ts` registers a `buildStart` plugin that shells out to
 * `pnpm generate-changelog`, and a `getGitVersion()` that shells out to `git`.
 * Neither is wanted on every unit-test run, so the two pieces the tests
 * actually need — the `@` alias and the `__APP_VERSION__` defines — are
 * restated here instead.
 */
export default defineConfig({
  plugins: [vue()],
  define: {
    __APP_VERSION__: JSON.stringify('0.0.0-test'),
    __APP_VERSION_DATE__: JSON.stringify('2026-01-01'),
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    // Vitest owns `src/**/__tests__/`, Playwright owns `e2e/` (its `testDir`).
    // The two globs cannot overlap, so neither runner can pick up the other's
    // files. `tsconfig.app.json` already excluded `src/**/__tests__/*` before
    // this config existed, which is why that location was chosen.
    include: ['src/**/__tests__/**/*.spec.ts'],
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
    // Node by default; the few DOM-bound suites opt in per file with
    // `// @vitest-environment jsdom`.
    environment: 'node',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/lib/**', 'src/composables/**', 'src/stores/**'],
      exclude: [
        // Generated from the OpenAPI schema — never hand-written, never tested.
        'src/client/**',
        // The tests themselves, and the golden fixtures they assert against.
        'src/**/__tests__/**',
      ],
    },
  },
})
