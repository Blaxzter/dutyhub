import { useLocalStorage } from '@vueuse/core'
import { watchEffect } from 'vue'

export type Palette = 'default' | 'classic'

const STORAGE_KEY = 'wirksam-palette'
const CLASSIC_CLASS = 'palette-classic'

const palette = useLocalStorage<Palette>(STORAGE_KEY, 'default')

watchEffect(() => {
  if (typeof document === 'undefined') return
  const html = document.documentElement
  if (palette.value === 'classic') html.classList.add(CLASSIC_CLASS)
  else html.classList.remove(CLASSIC_CLASS)
})

export function usePalette() {
  return palette
}
