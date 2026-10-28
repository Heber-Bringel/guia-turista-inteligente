import type { SessionUser } from '../types/api'

const SESSION_KEY = 'guia-turista:session:v2'
const SAVED_GOOGLE_KEY = 'guia_turista_saved_google_user'

function isSessionUser(value: unknown): value is SessionUser {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Record<string, unknown>
  return typeof candidate.id === 'string'
    && typeof candidate.nome === 'string'
    && (candidate.modo === 'google' || candidate.modo === 'visitante')
}

export function restoreSession(): SessionUser | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (!isSessionUser(parsed)) return null
    if (parsed.expiresAt && parsed.expiresAt <= Date.now()) {
      localStorage.removeItem(SESSION_KEY)
      return null
    }
    return parsed
  } catch {
    localStorage.removeItem(SESSION_KEY)
    return null
  }
}

export function saveSession(user: SessionUser): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify(user))
  if (user.modo === 'google') localStorage.setItem(SAVED_GOOGLE_KEY, JSON.stringify(user))
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_KEY)
}

export function restoreSavedGoogleUser(): SessionUser | null {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(SAVED_GOOGLE_KEY) ?? 'null')
    return isSessionUser(parsed) && parsed.modo === 'google' ? parsed : null
  } catch {
    localStorage.removeItem(SAVED_GOOGLE_KEY)
    return null
  }
}
