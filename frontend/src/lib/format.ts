import i18n from '@/locales/i18n'

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(i18n.global.locale.value)
}
