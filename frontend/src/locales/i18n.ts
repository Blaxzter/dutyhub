import { createI18n } from 'vue-i18n'

// Define types for the module structure
interface TranslationModule {
  default?: Record<string, unknown>
  [key: string]: unknown
}

interface ModuleMap {
  [path: string]: TranslationModule
}

interface Messages {
  [filename: string]: Record<string, unknown>
}

// Dynamically import all translation files
const enModules = import.meta.glob('@/locales/en/*.json', { eager: true }) as ModuleMap
const deModules = import.meta.glob('@/locales/de/*.json', { eager: true }) as ModuleMap

// Helper function to create messages object from modules
function createMessagesFromModules(modules: ModuleMap): Messages {
  const messages: Messages = {}

  Object.entries(modules).forEach(([path, module]) => {
    // Extract filename without extension from the path
    const filename = path.split('/').pop()?.replace('.json', '')

    if (filename) {
      messages[filename] = module.default || module
    }
  })

  return messages
}

// Create the complete translation objects
const enMessages: Messages = createMessagesFromModules(enModules)
const deMessages: Messages = createMessagesFromModules(deModules)

const supportedLocales = ['en', 'de']

function detectLocale(): string {
  const stored = localStorage.getItem('locale')
  if (stored) return stored
  const browserLang = navigator.language.split('-')[0]
  return supportedLocales.includes(browserLang) ? browserLang : 'en'
}

const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: 'en',
  messages: {
    en: enMessages,
    de: deMessages,
  },
})

export default i18n
