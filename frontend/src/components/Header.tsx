import { useEffect, useRef, useState } from 'react'
import { Compass, Globe, LogOut, MapPinned, Moon, RotateCcw, Sun, UserRound } from 'lucide-react'
import { getTranslations } from '../i18n/language'
import { LANGUAGE_OPTIONS } from '../i18n/translations'
import type { SessionUser, SupportedLanguage } from '../types/api'

interface HeaderProps {
  user: SessionUser | null
  authLoading: boolean
  onVisitorLogin: () => void
  onGoogleLogin: (credential: string) => void
  onLogout: () => void
  savedGoogleUser: SessionUser | null
  onRestoreGoogle: () => void
  theme: 'light' | 'dark'
  onToggleTheme: () => void
  language: SupportedLanguage
  onChangeLanguage: (language: SupportedLanguage) => void
}

const GOOGLE_SCRIPT_ID = 'google-identity-services'

export function Header({
  user,
  authLoading,
  onVisitorLogin,
  onGoogleLogin,
  onLogout,
  savedGoogleUser,
  onRestoreGoogle,
  theme,
  onToggleTheme,
  language,
  onChangeLanguage,
}: HeaderProps) {
  const googleButtonRef = useRef<HTMLDivElement>(null)
  const googleLoginRef = useRef(onGoogleLogin)
  const [googleUnavailable, setGoogleUnavailable] = useState(false)
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined
  const t = getTranslations(language)

  useEffect(() => {
    googleLoginRef.current = onGoogleLogin
  }, [onGoogleLogin])

  useEffect(() => {
    if (user || !clientId) return

    const render = () => {
      if (!window.google || !googleButtonRef.current) return
      googleButtonRef.current.replaceChildren()
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: ({ credential }) => credential && googleLoginRef.current(credential),
        auto_select: false,
      })
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        shape: 'rectangular',
        width: Math.min(320, googleButtonRef.current.clientWidth || 320),
      })
    }

    const existing = document.getElementById(GOOGLE_SCRIPT_ID) as HTMLScriptElement | null
    if (existing) {
      if (window.google) render()
      else existing.addEventListener('load', render, { once: true })
      return () => existing.removeEventListener('load', render)
    }

    const script = document.createElement('script')
    script.id = GOOGLE_SCRIPT_ID
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.addEventListener('load', render, { once: true })
    script.addEventListener('error', () => setGoogleUnavailable(true), { once: true })
    document.head.append(script)
    return () => script.removeEventListener('load', render)
  }, [clientId, user])

  const languagePicker = (
    <label className="language-picker">
      <Globe size={16} aria-hidden="true" />
      <select
        aria-label={t.languageSelectorLabel}
        value={language}
        onChange={(event) => onChangeLanguage(event.target.value as SupportedLanguage)}
      >
        {LANGUAGE_OPTIONS.map((option) => (
          <option key={option.code} value={option.code}>
            {option.nativeLabel}
          </option>
        ))}
      </select>
    </label>
  )

  return (
    <header className="topbar">
      <a className="brand" href="#main" aria-label={`${t.brandTitle} ${t.brandSubtitle}`}>
        <span className="brand-mark" aria-hidden="true"><Compass size={22} /></span>
        <span>
          <strong>{t.brandTitle}</strong>
          <small>{t.brandSubtitle}</small>
        </span>
      </a>

      {user ? (
        <div className="user-menu">
          {languagePicker}
          {user.foto ? <img src={user.foto} alt="" referrerPolicy="no-referrer" /> : <span className="avatar"><UserRound size={18} /></span>}
          <span className="user-copy">
            <strong>{user.nome}</strong>
            <small>{user.modo === 'visitante' ? t.visitorSession : user.email}</small>
          </span>
          {user.modo === 'google' && (
            <button className="button button-secondary restore-button" type="button" onClick={onVisitorLogin} disabled={authLoading}>
              <UserRound size={16} /> {t.visitorModeButton}
            </button>
          )}
          {user.modo === 'visitante' && savedGoogleUser && (
            <button className="button button-secondary restore-button" type="button" onClick={onRestoreGoogle}>
              <RotateCcw size={16} /> {t.restoreGooglePrefix} {savedGoogleUser.nome.split(' ')[0]}
            </button>
          )}
          <button
            className="button button-quiet button-icon theme-button"
            type="button"
            onClick={onToggleTheme}
            aria-label={theme === 'light' ? t.themeToDark : t.themeToLight}
          >
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
          <button className="button button-quiet button-icon" type="button" onClick={onLogout} aria-label={t.logoutAria}>
            <LogOut size={18} /> <span>{t.logout}</span>
          </button>
        </div>
      ) : (
        <div className="auth-actions" aria-busy={authLoading}>
          {languagePicker}
          <button
            className="button button-quiet button-icon theme-button"
            type="button"
            onClick={onToggleTheme}
            aria-label={theme === 'light' ? t.themeToDark : t.themeToLight}
          >
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
          {clientId && !googleUnavailable && <div className="google-button" ref={googleButtonRef} aria-label="Entrar com Google" />}
          <button className="button button-secondary" type="button" onClick={onVisitorLogin} disabled={authLoading}>
            <MapPinned size={18} />
            {authLoading ? t.signingIn : t.continueVisitor}
          </button>
        </div>
      )}
    </header>
  )
}
