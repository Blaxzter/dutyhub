interface AppConfig {
  LEGAL_NAME: string
  LEGAL_ADDRESS: string
  LEGAL_CITY: string
  LEGAL_EMAIL: string
  LEGAL_PHONE: string
  /** Cloudflare Turnstile site key. Empty means the bot check is switched off. */
  TURNSTILE_SITE_KEY: string
  /**
   * Whether the "try a demo event" entry points are offered.
   *
   * A string, not a boolean: this file describes what `config.js` can actually
   * contain, and `config.js` is written by a shell script substituting an
   * environment variable. Only the literal `'false'` switches the demo off —
   * see `stores/sandbox.ts`, which owns that reading — so an unset variable
   * leaves it on, matching the backend's own `SANDBOX_ENABLED` default.
   */
  SANDBOX_ENABLED: string
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
 * consequences are silent: an impressum reading "undefined", a widget that
 * renders against a broken `TURNSTILE_SITE_KEY` and a registration form nobody
 * can submit, or a `SANDBOX_ENABLED` nobody set that reads as "off" and quietly
 * takes the demo away from a deployment that never asked to lose it.
 *
 * Note that the safe default is not the same in each direction: an empty
 * Turnstile key means "no bot check", while an absent `SANDBOX_ENABLED` means
 * "demo on". Each default is the value that leaves the deployment working.
 */
const DEFAULTS: AppConfig = {
  LEGAL_NAME: '',
  LEGAL_ADDRESS: '',
  LEGAL_CITY: '',
  LEGAL_EMAIL: '',
  LEGAL_PHONE: '',
  TURNSTILE_SITE_KEY: '',
  SANDBOX_ENABLED: 'true',
}

export function useAppConfig(): AppConfig {
  return { ...DEFAULTS, ...window.__APP_CONFIG__ }
}
