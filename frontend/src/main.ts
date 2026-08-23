import { createApp } from 'vue'

import { createPinia } from 'pinia'

import { client } from '@/client/client.gen'
import { authSession } from '@/lib/auth-session'
import i18n from '@/locales/i18n.ts'
import { installFakeSession } from '@/testing/fake-session'

import App from './App.vue'
import './index.css'
import router from './router'

client.setConfig({
  baseURL: import.meta.env.VITE_API_URL,
  throwOnError: true, // Always throw errors instead of returning them
  // The refresh token lives in an httpOnly cookie, and a browser only attaches
  // cookies to a cross-origin request when it is asked to — which in
  // development every request is (:5555 to :8787). Without this the cookie is
  // simply never sent, `/auth/refresh` sees an anonymous caller, and every
  // reload signs the user out.
  withCredentials: true,
})

const app = createApp(App)

// E2E runs against a backend in TESTING mode that takes identity from the
// X-Test-User-Email header, so the browser half only has to *look* signed in.
// Double-gated on purpose: the build flag alone does nothing, the run has to
// opt in with the cookie as well.
if (import.meta.env.VITE_E2E_AUTH_BYPASS === 'true' && document.cookie.includes('e2e_bypass=1')) {
  installFakeSession()
} else {
  // Restore the session from the refresh cookie. Deliberately not awaited: the
  // app mounts immediately and `App.vue` shows a spinner until this settles,
  // while the route guards await the very same one-shot promise — so nothing is
  // ever decided against a session that has not been restored yet.
  void authSession.bootstrap()
}

app.use(createPinia())
app.use(router)
app.use(i18n)

app.mount('#app')

// Register service worker for push notifications
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch((error) => {
    console.warn('Service worker registration failed:', error)
  })
}
