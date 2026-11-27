import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertTriangle, ExternalLink, Info, Mail, Map, MessageCircle, Navigation, WifiOff } from 'lucide-react'
import { ChatRoteiro } from './components/ChatRoteiro'
import { DespachoModal } from './components/DespachoModal'
import { GuiaViajante } from './components/GuiaViajante'
import { Header } from './components/Header'
import { HistoricoViagens } from './components/HistoricoViagens'
import { MapaRota } from './components/MapaRota'
import { RoteiroForm } from './components/RoteiroForm'
import { TelemetriaCard } from './components/TelemetriaCard'
import {
  applyDocumentLanguage,
  getCurrentLanguage,
  getTranslations,
  setCurrentLanguage,
} from './i18n/language'
import {
  conversarRoteiro,
  despacharRoteiro,
  errorMessage,
  excluirRoteiro,
  listarRoteiros,
  loginGoogle,
  loginVisitante,
  marcarParadaVisitada,
  planejarRoteiro,
  transmitirGuia,
} from './services/api'
import { getCurrentPosition, isFarFromOrigin } from './services/geolocation'
import { clearSession, restoreSavedGoogleUser, restoreSession, saveSession } from './services/session'
import type { SessionUser, SupportedLanguage } from './types/api'
import type { CanalDespacho, Coordenada, PlanejamentoInput, Roteiro } from './types/roteiro'

type Notice = { tone: 'error' | 'warning' | 'info'; message: string } | null

export default function App() {
  const [user, setUser] = useState<SessionUser | null>(() => restoreSession())
  const [savedGoogleUser, setSavedGoogleUser] = useState<SessionUser | null>(() => restoreSavedGoogleUser())
  const [theme, setTheme] = useState<'light' | 'dark'>(() => localStorage.getItem('guia-turista:theme') === 'dark' ? 'dark' : 'light')
  const [language, setLanguage] = useState<SupportedLanguage>(() => getCurrentLanguage())
  const [authLoading, setAuthLoading] = useState(false)
  const [planning, setPlanning] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [locating, setLocating] = useState(false)
  const [history, setHistory] = useState<Roteiro[]>([])
  const [selected, setSelected] = useState<Roteiro | null>(null)
  const [lastPlanInput, setLastPlanInput] = useState<PlanejamentoInput | null>(null)
  const [currentPosition, setCurrentPosition] = useState<Coordenada | null>(null)
  const [guide, setGuide] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [dispatchChannel, setDispatchChannel] = useState<CanalDespacho | null>(null)
  const [notice, setNotice] = useState<Notice>(null)
  const [online, setOnline] = useState(navigator.onLine)
  const planningController = useRef<AbortController | null>(null)

  const t = getTranslations(language)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('guia-turista:theme', theme)
  }, [theme])

  useEffect(() => {
    applyDocumentLanguage(language)
  }, [language])

  useEffect(() => {
    const onOnline = () => setOnline(true)
    const onOffline = () => setOnline(false)
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    return () => {
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
    }
  }, [])

  const handleChangeLanguage = (nextLanguage: SupportedLanguage) => {
    const normalized = setCurrentLanguage(nextLanguage)
    setLanguage(normalized)
  }

  const loadHistory = useCallback(async (activeUser: SessionUser, activeLang: SupportedLanguage) => {
    setHistoryLoading(true)
    try {
      setHistory(await listarRoteiros(activeUser, undefined, activeLang))
    } catch (error) {
      setNotice({ tone: 'warning', message: errorMessage(error, activeLang) })
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  useEffect(() => {
    // A troca de identidade inicia a sincronização do histórico do usuário.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (user) void loadHistory(user, language)
    else {
      setHistory([])
      setSelected(null)
    }
  }, [language, loadHistory, user])

  useEffect(() => {
    if (!user?.expiresAt) return
    const remaining = user.expiresAt - Date.now()
    const expire = () => {
      clearSession()
      setUser(null)
      setNotice({ tone: 'info', message: getTranslations(language).sessionExpiredNotice })
    }
    if (remaining <= 0) {
      expire()
      return
    }
    const timer = window.setTimeout(expire, remaining)
    return () => window.clearTimeout(timer)
  }, [language, user])

  const commitUser = (nextUser: SessionUser) => {
    saveSession(nextUser)
    setUser(nextUser)
    if (nextUser.modo === 'google') setSavedGoogleUser(nextUser)
    setNotice(null)
  }

  const authenticate = async (action: () => Promise<SessionUser>) => {
    setAuthLoading(true)
    try {
      commitUser(await action())
    } catch (error) {
      setNotice({ tone: 'error', message: errorMessage(error, language) })
    } finally {
      setAuthLoading(false)
    }
  }

  const logout = () => {
    planningController.current?.abort()
    clearSession()
    setUser(null)
    setGuide('')
    setDispatchChannel(null)
    setNotice(null)
  }

  const locate = async () => {
    setLocating(true)
    try {
      setCurrentPosition(await getCurrentPosition())
      setNotice({ tone: 'info', message: t.locationSaved })
    } catch (error) {
      setNotice({ tone: 'warning', message: errorMessage(error, language) })
    } finally {
      setLocating(false)
    }
  }

  const streamGuide = async (
    roteiro: Roteiro,
    input: PlanejamentoInput,
    activeUser: SessionUser,
    signal: AbortSignal,
  ) => {
    setStreaming(true)
    setGuide('')
    try {
      let content = ''
      for await (const event of transmitirGuia(roteiro, input, activeUser, signal, language)) {
        content += event.chunk
        setGuide(content)
        if (event.done) break
      }
    } catch (error) {
      if (!(error instanceof DOMException && error.name === 'AbortError')) {
        setNotice({ tone: 'warning', message: t.guideWarningFriendly })
      }
    } finally {
      setStreaming(false)
    }
  }

  const plan = async (input: PlanejamentoInput) => {
    if (!user || planning) return
    planningController.current?.abort()
    const controller = new AbortController()
    planningController.current = controller
    setPlanning(true)
    setNotice(null)
    setLastPlanInput(input)
    try {
      const result = await planejarRoteiro(input, user, controller.signal, language)
      setSelected(result)
      setHistory((items) => [result, ...items.filter((item) => item.id !== result.id)])
      if (currentPosition && isFarFromOrigin(currentPosition, result.origem)) {
        setNotice({ tone: 'warning', message: t.farOriginWarning })
      }
      void streamGuide(result, input, user, controller.signal)
    } catch (error) {
      setNotice({ tone: 'error', message: errorMessage(error, language) })
    } finally {
      setPlanning(false)
    }
  }

  const remove = async (id: string) => {
    if (!user || !window.confirm(t.deleteConfirm)) return
    try {
      await excluirRoteiro(id, user, language)
      setHistory((items) => items.filter((item) => item.id !== id))
      if (selected?.id === id) setSelected(null)
    } catch (error) {
      setNotice({ tone: 'error', message: errorMessage(error, language) })
    }
  }

  const toggleVisit = async (attractionId: string, visited: boolean) => {
    if (!user || !selected) return
    try {
      const updated = await marcarParadaVisitada(selected.id, attractionId, visited, user, language)
      setSelected(updated)
      setHistory((items) => items.map((item) => item.id === updated.id ? updated : item))
    } catch (error) {
      setNotice({ tone: 'error', message: errorMessage(error, language) })
    }
  }

  const openMaps = () => {
    if (!selected) return
    window.open(
      `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(`${selected.origem.cidade}, ${selected.origem.uf}`)}&destination=${encodeURIComponent(`${selected.destino.cidade}, ${selected.destino.uf}`)}&travelmode=driving`,
      '_blank',
      'noopener,noreferrer',
    )
  }

  const activeGuideText = guide || selected?.guia || ''

  return (
    <div className="app-shell">
      <Header
        user={user}
        authLoading={authLoading}
        onVisitorLogin={() => void authenticate(() => loginVisitante(language))}
        onGoogleLogin={(credential) => void authenticate(() => loginGoogle(credential, language))}
        onLogout={logout}
        savedGoogleUser={savedGoogleUser}
        onRestoreGoogle={() => savedGoogleUser && commitUser(savedGoogleUser)}
        theme={theme}
        onToggleTheme={() => setTheme((value) => value === 'light' ? 'dark' : 'light')}
        language={language}
        onChangeLanguage={handleChangeLanguage}
      />

      {!online && (
        <div className="network-banner" role="status">
          <WifiOff size={16} /> {t.offlineBanner}
        </div>
      )}

      <main id="main" className="app-main">
        <section className="intro">
          <div>
            <span className="intro-mark"><Navigation size={18} /> {t.introMark}</span>
            <h2>{t.introHeading}</h2>
            <p>{t.introBody}</p>
          </div>
          <div className="intro-route" aria-hidden="true">
            <span>{t.introOrigin}</span>
            <i />
            <span>{t.introDestination}</span>
          </div>
        </section>

        {notice && (
          <div className={`notice notice-${notice.tone}`} role={notice.tone === 'error' ? 'alert' : 'status'}>
            {notice.tone === 'info' ? <Info /> : <AlertTriangle />}
            <span>{notice.message}</span>
            <button type="button" onClick={() => setNotice(null)} aria-label="Fechar aviso">×</button>
          </div>
        )}

        {!user ? (
          <section className="signin-gate">
            <Map size={36} />
            <h1>{t.signinHeading}</h1>
            <p>{t.signinBody}</p>
            <button
              className="button button-primary"
              onClick={() => void authenticate(() => loginVisitante(language))}
              disabled={authLoading}
            >
              {authLoading ? t.signinLoading : t.signinButton}
            </button>
          </section>
        ) : (
          <div className="workspace">
            <div className="workspace-main">
              <RoteiroForm
                loading={planning}
                disabled={!online}
                onSubmit={(values) => void plan(values)}
                onLocate={() => void locate()}
                locating={locating}
                language={language}
                {...(currentPosition ? { currentPosition } : {})}
              />

              {planning && (
                <section className="result-skeleton" aria-label={t.planningButton}>
                  <div /><span /><span /><span />
                </section>
              )}

              {selected && !planning && (
                <section className="result-panel" aria-labelledby="result-title">
                  <div className="result-header">
                    <div>
                      <span>{t.calculatedRoute}</span>
                      <h2 id="result-title">
                        {selected.origem.cidade} <i aria-hidden="true">→</i> {selected.destino.cidade}
                      </h2>
                    </div>
                    <div className="result-actions">
                      <button className="button button-secondary" type="button" onClick={openMaps}>
                        <ExternalLink size={16} /> {t.mapsButton}
                      </button>
                      <button
                        className="button button-primary"
                        type="button"
                        onClick={() => setDispatchChannel('email')}
                      >
                        <Mail size={16} /> {t.sendEmailButton}
                      </button>
                      <button
                        className="button button-secondary"
                        type="button"
                        onClick={() => setDispatchChannel('whatsapp')}
                      >
                        <MessageCircle size={16} /> {t.sendWhatsAppButton}
                      </button>
                    </div>
                  </div>

                  <MapaRota roteiro={selected} language={language} />
                  <TelemetriaCard roteiro={selected} language={language} />

                  <details className="elevation-details">
                    <summary>{t.elevationSummary}</summary>
                    <dl>
                      <div>
                        <dt>{t.maxAltitude}</dt>
                        <dd>
                          {selected.altimetria?.altitude_maxima_m === undefined
                            ? '—'
                            : `${Math.round(selected.altimetria.altitude_maxima_m)} m`}
                        </dd>
                      </div>
                      <div>
                        <dt>{t.ascentDescent}</dt>
                        <dd>
                          +{Math.round(selected.altimetria?.ganho_m ?? 0)} m / −{Math.round(selected.altimetria?.perda_m ?? 0)} m
                        </dd>
                      </div>
                      <div>
                        <dt>{t.consumptionImpact}</dt>
                        <dd>
                          {selected.altimetria?.impacto_consumo_percentual === undefined
                            ? '—'
                            : `${selected.altimetria.impacto_consumo_percentual > 0 ? '+' : ''}${selected.altimetria.impacto_consumo_percentual.toFixed(1)}%`}
                        </dd>
                      </div>
                    </dl>
                  </details>

                  <GuiaViajante
                    roteiro={selected}
                    text={activeGuideText}
                    streaming={streaming}
                    language={language}
                    onToggleVisit={(id, visited) => void toggleVisit(id, visited)}
                  />

                  <ChatRoteiro
                    key={selected.id}
                    roteiro={selected}
                    language={language}
                    {...(lastPlanInput ? { diasEstadia: lastPlanInput.dias, estiloViagem: lastPlanInput.estilo_viagem } : {})}
                    onSendMessage={(payload) => conversarRoteiro(payload, user, language)}
                    onSummaryUpdated={(summary) => setGuide(summary)}
                  />
                </section>
              )}
            </div>

            <HistoricoViagens
              items={history}
              loading={historyLoading}
              language={language}
              {...(selected ? { selectedId: selected.id } : {})}
              onSelect={(item) => {
                setSelected(item)
                setGuide(item.guia ?? '')
              }}
              onDelete={(id) => void remove(id)}
            />
          </div>
        )}
      </main>

      {selected && user && dispatchChannel && (
        <DespachoModal
          key={`${selected.id}-${dispatchChannel}`}
          initialChannel={dispatchChannel}
          roteiro={selected}
          guideText={activeGuideText}
          userName={user.nome}
          {...(user.email ? { userEmail: user.email } : {})}
          language={language}
          onClose={() => setDispatchChannel(null)}
          onDispatch={(payload) => despacharRoteiro(payload, user, language)}
        />
      )}

      <footer className="footer">
        <span>{t.footerLeft}</span>
        <span>{t.footerRight}</span>
      </footer>
    </div>
  )
}
