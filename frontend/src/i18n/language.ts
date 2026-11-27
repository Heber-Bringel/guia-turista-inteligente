import type { SupportedLanguage } from '../types/api'
import { LANGUAGE_OPTIONS, TRANSLATIONS, type TranslationKeys } from './translations'

const STORAGE_KEY = 'guia-turista:lang'
const VALID_CODES = new Set<string>(LANGUAGE_OPTIONS.map((option) => option.code))

export function isSupportedLanguage(value: string): value is SupportedLanguage {
  return VALID_CODES.has(value)
}

function readStoredLanguage(): SupportedLanguage {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved && isSupportedLanguage(saved)) return saved
  } catch {
    // Ambientes sem acesso a localStorage usam o padrão pt-BR.
  }
  return 'pt-BR'
}

let currentLanguage: SupportedLanguage = readStoredLanguage()

export function getDirection(lang: SupportedLanguage): 'ltr' | 'rtl' {
  return lang === 'ar' ? 'rtl' : 'ltr'
}

export function applyDocumentLanguage(lang: SupportedLanguage): void {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = lang
    document.documentElement.dir = getDirection(lang)
  }
}

export function getCurrentLanguage(): SupportedLanguage {
  return currentLanguage
}

export function setCurrentLanguage(lang: string): SupportedLanguage {
  const normalized: SupportedLanguage = isSupportedLanguage(lang) ? lang : 'pt-BR'
  currentLanguage = normalized
  try {
    localStorage.setItem(STORAGE_KEY, normalized)
  } catch {
    // Ignora falha de escrita em modo privado restrito.
  }
  applyDocumentLanguage(normalized)
  return normalized
}

export function resetLanguageFromStorage(): SupportedLanguage {
  currentLanguage = readStoredLanguage()
  applyDocumentLanguage(currentLanguage)
  return currentLanguage
}

export function getTranslations(lang?: SupportedLanguage): TranslationKeys {
  return TRANSLATIONS[lang ?? currentLanguage]
}
