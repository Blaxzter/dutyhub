interface AppConfig {
  LEGAL_NAME: string
  LEGAL_ADDRESS: string
  LEGAL_CITY: string
  LEGAL_EMAIL: string
  LEGAL_PHONE: string
  /** Cloudflare Turnstile site key. Empty means the bot check is switched off. */
  TURNSTILE_SITE_KEY: string
}

declare global {
  interface Window {
    __APP_CONFIG__?: Partial<AppConfig>
  }
}

/**
 * Runtime configuration, read fresh from `window.__APP_CONFIG__` on every call.
 *
 * `public/config.js` holds the development copy and `docker-entrypoint.sh`
 * rewrites it from environment variables before nginx starts — which is what
 * lets one built image serve two deployments with different legal details and
 * different Turnstile keys.
 *
 * The defaults are merged **per field**, not used as an all-or-nothing
 * fallback. A `config.js` written before a key existed is otherwise a perfectly
 * valid object that happens to answer `undefined` for the new one, and the
 * consequences are silent: an impressum reading "undefined", or — for
 * `TURNSTILE_SITE_KEY` — a widget that renders against a broken key and a
 * registration form nobody can submit.
 */
const DEFAULTS: AppConfig = {
  LEGAL_NAME: '',
  LEGAL_ADDRESS: '',
  LEGAL_CITY: '',
  LEGAL_EMAIL: '',
  LEGAL_PHONE: '',
  TURNSTILE_SITE_KEY: '',
}

export function useAppConfig(): AppConfig {
  return { ...DEFAULTS, ...window.__APP_CONFIG__ }
}
