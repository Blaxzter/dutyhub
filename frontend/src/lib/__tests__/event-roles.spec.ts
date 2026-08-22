import { describe, expect, it } from 'vitest'

import {
  EVENT_ROLES,
  type EventRole,
  roleAtLeast,
  roleLabelKey,
} from '@/lib/event-roles'

describe('EVENT_ROLES', () => {
  it('lists every role exactly once', () => {
    expect([...EVENT_ROLES]).toEqual(['owner', 'admin', 'member'])
    expect(new Set(EVENT_ROLES).size).toBe(EVENT_ROLES.length)
  })
})

describe('roleAtLeast', () => {
  // The hierarchy is the whole point of this module, so it is asserted as a
  // full matrix rather than a handful of spot checks — a silent reordering of
  // the internal array would otherwise only surface as a permission bug.
  const EXPECTED: Array<[EventRole, EventRole, boolean]> = [
    ['owner', 'owner', true],
    ['owner', 'admin', true],
    ['owner', 'member', true],
    ['admin', 'owner', false],
    ['admin', 'admin', true],
    ['admin', 'member', true],
    ['member', 'owner', false],
    ['member', 'admin', false],
    ['member', 'member', true],
  ]

  it.each(EXPECTED)('%s meets a minimum of %s → %s', (role, minimum, expected) => {
    expect(roleAtLeast(role, minimum)).toBe(expected)
  })

  describe('when the caller holds no role', () => {
    // A non-member must never clear a bar, including the lowest one — this is
    // the branch that decides whether a stranger sees an event at all.
    it.each([
      ['null', null],
      ['undefined', undefined],
    ])('%s never meets any minimum', (_label, role) => {
      for (const minimum of EVENT_ROLES) {
        expect(roleAtLeast(role, minimum)).toBe(false)
      }
    })
  })

  it('is reflexive for every role', () => {
    for (const role of EVENT_ROLES) {
      expect(roleAtLeast(role, role)).toBe(true)
    }
  })

  it('is transitive: owner clears anything admin clears', () => {
    for (const minimum of EVENT_ROLES) {
      if (roleAtLeast('admin', minimum)) {
        expect(roleAtLeast('owner', minimum)).toBe(true)
      }
    }
  })
})

describe('roleLabelKey', () => {
  it.each(EVENT_ROLES)('builds the i18n key for %s', (role) => {
    expect(roleLabelKey(role)).toBe(`duties.events.roles.${role}`)
  })

  it('returns keys that differ per role', () => {
    const keys = EVENT_ROLES.map(roleLabelKey)
    expect(new Set(keys).size).toBe(EVENT_ROLES.length)
  })
})
