<script setup lang="ts">
/**
 * The Cloudflare Turnstile challenge on the registration form.
 *
 * Turnstile is a CAPTCHA that usually shows nobody a puzzle: it scores the
 * browser from signals it already has and only escalates to something clickable
 * when that score is poor. So the honest description of this component is "a
 * box that is normally a tick", and it is placed and worded accordingly.
 *
 * ── Explicit rendering, not the `cf-turnstile` class ────────────────────────
 * Cloudflare's implicit mode scans the DOM once on script load. This is a
 * single-page app: the register view is mounted by the router long after that
 * scan, and on the second visit the container is a different element. So the
 * script is loaded with `render=explicit` and `turnstile.render()` is called
 * from `onMounted`, which is the mode Cloudflare documents for exactly this.
 *
 * ── The token is single-use, and that shapes the whole API ──────────────────
 * Cloudflare answers `timeout-or-duplicate` to a token it has already seen, and
 * it also expires on its own after a few minutes. Two consequences the parent
 * has to honour, which is why `reset()` is exposed rather than kept private:
 *
 *   · a **failed** submission (say, the address was already taken) must reset
 *     the widget before the next attempt, or every retry is refused by
 *     Cloudflare for a reason that has nothing to do with what the person
 *     fixed;
 *   · an expiring token clears itself through `update:token` with `null`, so a
 *     form left open over lunch disables its submit button instead of posting a
 *     token the server will reject.
 *
 * ── Failing visibly ─────────────────────────────────────────────────────────
 * If the script cannot load — an ad blocker, an offline moment, a corporate
 * proxy — there is no token to be had, and the server (which fails closed) will
 * refuse the registration. Saying so here is the difference between "the button
 * is greyed out and I don't know why" and a sentence naming the problem.
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { useI18n } from 'vue-i18n'

/** Cloudflare's own subset of the render options — only what this app sets. */
interface TurnstileRenderOptions {
  sitekey: string
  theme?: 'light' | 'dark' | 'auto'
  language?: string
  action?: string
  callback?: (token: string) => void
  'error-callback'?: (code?: string) => void
  'expired-callback'?: () => void
  'timeout-callback'?: () => void
}

interface TurnstileApi {
  render: (container: HTMLElement, options: TurnstileRenderOptions) => string | undefined
  reset: (widgetId?: string) => void
  remove: (widgetId?: string) => void
}

declare global {
  interface Window {
    turnstile?: TurnstileApi
  }
}

/**
 * The name of the global Cloudflare calls once its bootstrap has finished.
 *
 * `api.js` insists on being told when it is ready rather than letting you infer
 * it: its own `turnstile.ready()` helper *throws* on a script tag carrying
 * `async` or `defer` ("Remove async/defer … before using turnstile.ready()"),
 * and a dynamically inserted tag is always async. `onload=` is the documented
 * signal for exactly this case, so the callback goes on `window` under a name
 * unlikely to collide and is deleted the moment it fires.
 */
const ONLOAD_CALLBACK = '__wirksamTurnstileReady'
const SCRIPT_SRC = `https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=${ONLOAD_CALLBACK}`

/**
 * One script tag per document, shared by every widget that ever mounts.
 *
 * Kept at module scope on purpose: the register and login views could both want
 * a challenge one day, and appending the script twice makes Cloudflare log a
 * duplicate-load warning and re-run its bootstrap. The promise is cleared on
 * failure so a later mount — after the network came back — gets a fresh attempt
 * rather than the cached rejection.
 */
let scriptPromise: Promise<TurnstileApi> | null = null

function loadTurnstile(): Promise<TurnstileApi> {
  if (window.turnstile) return Promise.resolve(window.turnstile)
  if (scriptPromise) return scriptPromise

  scriptPromise = new Promise<TurnstileApi>((resolve, reject) => {
    Reflect.set(window, ONLOAD_CALLBACK, () => {
      Reflect.deleteProperty(window, ONLOAD_CALLBACK)
      const api = window.turnstile
      if (api) resolve(api)
      else reject(new Error('Turnstile signalled ready without exposing its API'))
    })

    const script = document.createElement('script')
    script.src = SCRIPT_SRC
    script.async = true
    script.defer = true
    script.addEventListener('error', () => {
      Reflect.deleteProperty(window, ONLOAD_CALLBACK)
      scriptPromise = null
      reject(new Error('Turnstile script could not be loaded'))
    })
    document.head.append(script)
  })

  return scriptPromise
}

const props = defineProps<{
  /** Public site key. The parent decides whether to render this at all. */
  siteKey: string
  /**
   * Labels the challenge in Cloudflare's analytics — one sitekey, several
   * forms, and a per-form success rate you can actually read.
   */
  action?: string
}>()

const emit = defineEmits<{
  /** The solved token, or `null` when it expired, errored or was reset. */
  'update:token': [token: string | null]
}>()

const { t, locale } = useI18n()

const container = ref<HTMLElement | null>(null)
const failed = ref(false)

let widgetId: string | undefined
let api: TurnstileApi | undefined
/**
 * Bumped on every teardown. An async `render` that was already in flight when
 * the component unmounted (or when the locale changed) must not attach a widget
 * to a container that is gone, so it compares the epoch it captured against the
 * current one before touching anything.
 */
let epoch = 0

/**
 * Dark mode is class-based here — a viewer can override their system setting —
 * so the `dark` class on `<html>` decides rather than `prefers-color-scheme`.
 * Turnstile's own `auto` reads the media query and would show a light widget on
 * a dark page for anyone who made that choice.
 */
function currentTheme(): 'light' | 'dark' {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

function teardown(): void {
  epoch += 1
  if (api && widgetId !== undefined) api.remove(widgetId)
  widgetId = undefined
}

async function render(): Promise<void> {
  const mine = ++epoch
  failed.value = false

  let loaded: TurnstileApi
  try {
    loaded = await loadTurnstile()
  } catch {
    if (mine === epoch) {
      failed.value = true
      emit('update:token', null)
    }
    return
  }

  if (mine !== epoch || !container.value) return
  api = loaded

  widgetId = loaded.render(container.value, {
    sitekey: props.siteKey,
    theme: currentTheme(),
    language: locale.value,
    action: props.action,
    callback: (token: string) => emit('update:token', token),
    // Cloudflare hands the widget its own retry affordance, so this only has to
    // make sure no stale token survives the error.
    'error-callback': () => emit('update:token', null),
    'expired-callback': () => emit('update:token', null),
    'timeout-callback': () => emit('update:token', null),
  })
}

/**
 * Throw away the current token and re-run the challenge.
 *
 * The parent calls this after a rejected submission — see the note above on
 * `timeout-or-duplicate`.
 */
function reset(): void {
  emit('update:token', null)
  if (api && widgetId !== undefined) api.reset(widgetId)
}

defineExpose({ reset })

onMounted(render)
onBeforeUnmount(teardown)

// Language is fixed at render time, so switching locale means a new widget.
// Rare enough that the flicker costs nothing, and the alternative is a German
// page with an English challenge in the middle of it.
watch(locale, () => {
  teardown()
  emit('update:token', null)
  void render()
})
</script>

<template>
  <div>
    <div ref="container" data-testid="turnstile-widget" />
    <p
      v-if="failed"
      class="text-sm text-destructive"
      role="alert"
      data-testid="turnstile-unavailable"
    >
      {{ t('auth.register.securityCheck.unavailable') }}
    </p>
  </div>
</template>
