import type { ComputedRef } from 'vue'

import { createContext } from 'reka-ui'

/**
 * Where a dialog stops being a dialog.
 *
 * Tailwind's `md` boundary on purpose: it is the same line `MobileBottomNav`
 * draws with `md:hidden` and the one the sidebar collapses to a Sheet at, so a
 * viewport can never end up with the phone shell and a centred desktop modal at
 * once. Change it here and every dialog in the app moves together.
 */
export const RESPONSIVE_DIALOG_MOBILE_QUERY = '(max-width: 767px)'

/**
 * `Dialog` and `Drawer` are two unrelated reka-ui primitives — a title has to
 * be a `DialogTitle` inside one and a `DrawerTitle` inside the other for the
 * `aria-labelledby` wiring to land. Rather than have every part re-run the
 * media query (and risk two parts disagreeing mid-resize), the root decides
 * once and the parts read the answer from here.
 */
export const [useResponsiveDialog, provideResponsiveDialogContext] = createContext<{
  /** True while this dialog is rendering as a bottom drawer. */
  isMobile: ComputedRef<boolean>
}>('ResponsiveDialog')
