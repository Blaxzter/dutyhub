/**
 * The messages a visitor sees when a form is wrong.
 *
 * These assert against *keys*, not sentences: the translator owns the wording,
 * and a spec that pins the wording turns every copy edit into a failing test.
 * What is worth pinning is the mapping — above all that `.min(1)` reads as
 * "required" rather than "use at least 1 character", because that single branch
 * is what lets a generated schema's `name` and a hand-written `password` share
 * one rule and still say the right thing.
 */
import { afterEach, describe, expect, it } from 'vitest'
import * as z from 'zod'

import { createZodErrorMap, installZodI18n } from '../zod-i18n'

/** Renders `key` / `key:arg` so both the lookup and the interpolation are visible. */
const t = (key: string, named?: Record<string, unknown>) =>
  named ? `${key}:${Object.values(named).join(',')}` : key

const errorMap = createZodErrorMap(t)

// `installZodI18n` writes to Zod's process-wide config, so the one test that
// exercises it has to put the default back or it leaks into every later parse.
afterEach(() => {
  z.config({ customError: undefined })
})

/** Every issue a parse produced, keyed by its top-level field. */
function messagesFor(schema: z.ZodType, value: unknown): Record<string, string> {
  const result = schema.safeParse(value, { error: errorMap })
  if (result.success) return {}
  return Object.fromEntries(
    result.error.issues.map((issue) => [String(issue.path[0] ?? '_'), issue.message]),
  )
}

/** The shape of the real register form, including the rules it adds itself. */
const registerLike = z.object({
  email: z.email(),
  name: z.string().min(1).max(100),
  password: z.string().min(8),
})

describe('createZodErrorMap', () => {
  it('calls an absent field required rather than a type error', () => {
    expect(messagesFor(registerLike, {})).toEqual({
      email: 'common.validation.required',
      name: 'common.validation.required',
      password: 'common.validation.required',
    })
  })

  it('treats an empty box as unfilled, not as a malformed address', () => {
    const messages = messagesFor(registerLike, { email: '', name: '', password: '' })
    expect(messages.email).toBe('common.validation.required')
    // `.min(1)` is how a generated schema spells "required".
    expect(messages.name).toBe('common.validation.required')
  })

  it('names the email rule once something has actually been typed', () => {
    const messages = messagesFor(registerLike, { email: 'nope', name: 'Alex', password: 'abcdefgh' })
    expect(messages.email).toBe('common.validation.email')
  })

  it('passes the bound through for real length rules', () => {
    const messages = messagesFor(registerLike, {
      email: 'a@b.co',
      name: 'a'.repeat(101),
      password: 'short',
    })
    expect(messages.password).toBe('common.validation.tooShort:8')
    expect(messages.name).toBe('common.validation.tooLong:100')
  })

  it('counts things rather than characters for lists', () => {
    const schema = z.object({ picks: z.array(z.string()).min(2).max(3) })
    expect(messagesFor(schema, { picks: ['a'] }).picks).toBe('common.validation.listMin:2')
    expect(messagesFor(schema, { picks: ['a', 'b', 'c', 'd'] }).picks).toBe(
      'common.validation.listMax:3',
    )
  })

  it('calls an empty required list unfilled rather than too short', () => {
    // `.min(1)` on a list means the same thing it means on a string: pick one.
    const schema = z.object({ picks: z.array(z.string()).min(1) })
    expect(messagesFor(schema, { picks: [] }).picks).toBe('common.validation.required')
  })

  it('treats an explicit null the same as a missing field', () => {
    // Some payloads spell "nothing" as `null` rather than by leaving the key
    // out; both mean the visitor has not answered.
    const schema = z.object({ name: z.string() })
    expect(messagesFor(schema, { name: null }).name).toBe('common.validation.required')
  })

  it('names a malformed web address', () => {
    const schema = z.object({ site: z.url() })
    expect(messagesFor(schema, { site: 'not a url' }).site).toBe('common.validation.url')
  })

  it('describes a number as a bound rather than a length', () => {
    const schema = z.object({ places: z.number().min(1).max(20) })
    expect(messagesFor(schema, { places: 0 }).places).toBe('common.validation.numberMin:1')
    expect(messagesFor(schema, { places: 99 }).places).toBe('common.validation.numberMax:20')
  })

  it('falls back to a sentence instead of Zod jargon for anything unmapped', () => {
    const schema = z.object({ step: z.number().multipleOf(5) })
    expect(messagesFor(schema, { step: 7 }).step).toBe('common.validation.invalid')
  })

  it('says nothing about a format it cannot name in plain words', () => {
    const schema = z.object({ code: z.string().regex(/^[A-Z]{3}$/) })
    expect(messagesFor(schema, { code: 'ab' }).code).toBe('common.validation.invalid')
  })

  it('never overrides a message the schema wrote for itself', () => {
    const schema = z.object({ password: z.string().min(8, 'the form knows better') })
    expect(messagesFor(schema, { password: 'x' }).password).toBe('the form knows better')
  })

  it('reaches schemas that were built long before it was installed', () => {
    // The point of installing globally: `client/zod.gen.ts` is evaluated at
    // import time and can never be rebuilt, so the map has to apply to schemas
    // that already exist. Zod resolves the message at *parse* time, which is
    // what makes that work.
    const built = z.object({ email: z.email() })
    expect(built.safeParse({ email: '' }).error?.issues[0]?.message).toBe('Invalid email address')

    installZodI18n(t)

    expect(built.safeParse({ email: '' }).error?.issues[0]?.message).toBe(
      'common.validation.required',
    )
  })

  it('reads the translator afresh on every issue, so a language switch lands', () => {
    let locale = 'en'
    const map = createZodErrorMap((key) => `${locale}:${key}`)
    const schema = z.string().min(1)

    expect(schema.safeParse('', { error: map }).error?.issues[0]?.message).toBe(
      'en:common.validation.required',
    )
    locale = 'de'
    expect(schema.safeParse('', { error: map }).error?.issues[0]?.message).toBe(
      'de:common.validation.required',
    )
  })
})
