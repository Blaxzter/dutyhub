/**
 * Per-event roles.
 *
 * Authorisation lives on the event, not on the account: the only global role
 * left is the platform superadmin. The generated client spells these out as
 * inline string unions on each schema, so the shared names live here.
 */

export const EVENT_ROLES = ['owner', 'admin', 'member'] as const

export type EventRole = (typeof EVENT_ROLES)[number]

/** Roles that can be handed out directly. Ownership moves via transfer only. */
export type AssignableEventRole = Exclude<EventRole, 'owner'>

/** Weakest → strongest. Comparing positions is the whole hierarchy. */
const ORDER: readonly EventRole[] = ['member', 'admin', 'owner']

export function roleAtLeast(role: EventRole | null | undefined, minimum: EventRole): boolean {
  if (!role) return false
  return ORDER.indexOf(role) >= ORDER.indexOf(minimum)
}

/** i18n key for a role's display name, e.g. `events.roles.admin`. */
export function roleLabelKey(role: EventRole): string {
  return `duties.events.roles.${role}`
}

export type EventVisibility = 'public' | 'private'
