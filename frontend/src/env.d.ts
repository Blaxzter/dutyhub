/// <reference types="vite/client" />

declare const __APP_VERSION__: string
declare const __APP_VERSION_DATE__: string

interface ImportMetaEnv {
  readonly VITE_AUTH0_DOMAIN: string
  readonly VITE_AUTH0_CLIENT_ID: string
  readonly VITE_AUTH0_API_AUDIENCE: string
  readonly VITE_AUTH0_CALLBACK_URL?: string
  readonly VITE_API_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
