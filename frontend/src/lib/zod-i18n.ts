/**
 * Project-voice messages for every Zod issue the app can raise.
 *
 * Importing `zod` installs its English locale as the lowest-priority error map
 * (`zod/v4/classic/external.js` runs `config(en())`), and the schemas in
 * `client/zod.gen.ts` are generated from the OpenAPI document and carry no
 * messages of their own. That is the whole story behind "Invalid input" and
 * "Too small: expected string to have >=8 characters" appearing under a German
 * label — nothing ever overrode the default.
 *
 * The generated file may never be hand-edited, so the words arrive from
 * outside. Zod resolves a message in this order:
 *
 *   schema-level message → per-parse `error` → config().customError → locale
 *
 * which is exactly the precedence needed: a form that writes its own message
 * still wins, and nothing is left speaking Zod's dialect. The map is read at
 * *parse* time (`zod/v4/core/parse.js` finalises each issue against the current
 * config), so every schema built long before this runs — all of `zod.gen.ts` —
 * picks the messages up on its next validation, with nothing to rebuild.
 *
 * Note this only governs messages produced *from now on*. Errors already on
 * screen when the language changes are vee-validate's business: it re-validates
 * when the schema *reference* changes, which is why each auth view wraps its
 * schema in a `computed` that reads `locale`.
 */
import type { core } from 'zod'
import { config } from 'zod'

/** `t` from `useI18n()` / `i18n.global`, narrowed to what this file uses. */
export type Translate = (key: string, named?: Record<string, unknown>) => string

/** Origins whose size is a count of things rather than a length in characters. */
const COUNTED_ORIGINS = new Set(['array', 'set', 'file', 'map'])

/** Formats worth naming. Anything else would show the visitor a regex. */
const FORMAT_KEYS: Record<string, string> = {
  email: 'common.validation.email',
  url: 'common.validation.url',
}

/**
 * One issue, one sentence.
 *
 * Deliberately keyed on what a constraint *means* and never on `issue.path`:
 * these schemas are generated from the backend's OpenAPI document, and their
 * field names are not ours to depend on.
 *
 * The `min <= 1` branch is the load-bearing one. `.min(1)` on a string is how a
 * generated schema spells "required", so it says so — which is the only reason
 * `name` (min 1) and `password` (min 8) can share a single rule and still read
 * correctly. The same goes for an empty string failing `z.email()`: an untouched
 * box is not a malformed address.
 */
export function messageForIssue(issue: core.$ZodRawIssue, t: Translate): string {
  switch (issue.code) {
    case 'invalid_type':
      // A field nobody filled in arrives as `undefined`. A genuinely wrong type
      // is a bug on our side, and not something to describe to a visitor.
      return issue.input === undefined || issue.input === null
        ? t('common.validation.required')
        : t('common.validation.invalid')

    case 'invalid_format': {
      if (issue.input === '') return t('common.validation.required')
      const key = FORMAT_KEYS[issue.format]
      return key ? t(key) : t('common.validation.invalid')
    }

    case 'too_small': {
      const min = Number(issue.minimum)
      if (issue.origin === 'string') {
        return min <= 1
          ? t('common.validation.required')
          : t('common.validation.tooShort', { min })
      }
      if (COUNTED_ORIGINS.has(issue.origin)) {
        return min <= 1 ? t('common.validation.required') : t('common.validation.listMin', { min })
      }
      return t('common.validation.numberMin', { min })
    }

    case 'too_big': {
      const max = Number(issue.maximum)
      if (issue.origin === 'string') return t('common.validation.tooLong', { max })
      if (COUNTED_ORIGINS.has(issue.origin)) return t('common.validation.listMax', { max })
      return t('common.validation.numberMax', { max })
    }

    default:
      // not_multiple_of, unrecognized_keys, invalid_union, invalid_value and
      // anything a future Zod adds. A generic sentence beats Zod's wording,
      // which is written for whoever wrote the schema, not for whoever is
      // filling in the form.
      return t('common.validation.invalid')
  }
}

/** Build the error map. Exported separately so it is testable without global state. */
export function createZodErrorMap(t: Translate): core.$ZodErrorMap {
  return (issue) => messageForIssue(issue, t)
}

/** Install the map process-wide. Called once, from `locales/i18n.ts`. */
export function installZodI18n(t: Translate): void {
  config({ customError: createZodErrorMap(t) })
}
