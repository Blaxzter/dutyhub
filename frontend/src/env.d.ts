/// <reference types="vite/client" />

declare const __APP_VERSION__: string
declare const __APP_VERSION_DATE__: string

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  /**
   * `'true'` arms the E2E sign-in bypass. It is only half a gate: the run must
   * also carry an `e2e_bypass=1` cookie, and identity is still asserted
   * server-side by the `X-Test-User-Email` header against a TESTING backend.
   */
  readonly VITE_E2E_AUTH_BYPASS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
