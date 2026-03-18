interface AppConfig {
  LEGAL_NAME: string
  LEGAL_ADDRESS: string
  LEGAL_CITY: string
  LEGAL_EMAIL: string
  LEGAL_PHONE: string
}

declare global {
  interface Window {
    __APP_CONFIG__?: AppConfig
  }
}

export function useAppConfig(): AppConfig {
  return (
    window.__APP_CONFIG__ ?? {
      LEGAL_NAME: '',
      LEGAL_ADDRESS: '',
      LEGAL_CITY: '',
      LEGAL_EMAIL: '',
      LEGAL_PHONE: '',
    }
  )
}
