import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertTriangle, Download, ExternalLink, Info, Map, MessageCircle, Navigation, WifiOff } from 'lucide-react'
import { Header } from './components/Header'
import { HistoricoViagens } from './components/HistoricoViagens'
import { GuiaViajante } from './components/GuiaViajante'
import { MapaRota } from './components/MapaRota'
import { RoteiroForm } from './components/RoteiroForm'
import { TelemetriaCard } from './components/TelemetriaCard'
import { baixarGpx, errorMessage, excluirRoteiro, listarRoteiros, loginGoogle, loginVisitante, marcarParadaVisitada, planejarRoteiroComTelemetria, transmitirGuia } from './services/api'
import { getCurrentPosition, isFarFromOrigin } from './services/geolocation'
import { clearSession, restoreSavedGoogleUser, restoreSession, saveSession } from './services/session'
import type { RequestTelemetry, SessionUser } from './types/api'
import type { Coordenada, PlanejamentoInput, Roteiro } from './types/roteiro'

type Notice = { tone: 'error' | 'warning' | 'info'; message: string } | null

export default function App() {
  const [user, setUser] = useState<SessionUser | null>(() => restoreSession())
  const [savedGoogleUser, setSavedGoogleUser] = useState<SessionUser | null>(() => restoreSavedGoogleUser())
  const [theme, setTheme] = useState<'light' | 'dark'>(() => localStorage.getItem('guia-turista:theme') === 'dark' ? 'dark' : 'light')
  const [authLoading, setAuthLoading] = useState(false)
  const [planning, setPlanning] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [locating, setLocating] = useState(false)
  const [history, setHistory] = useState<Roteiro[]>([])
  const [selected, setSelected] = useState<Roteiro | null>(null)
  const [currentPosition, setCurrentPosition] = useState<Coordenada | null>(null)
  const [guide, setGuide] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [notice, setNotice] = useState<Notice>(null)
  const [telemetry, setTelemetry] = useState<RequestTelemetry | undefined>()
  const [online, setOnline] = useState(navigator.onLine)
  const planningController = useRef<AbortController | null>(null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('guia-turista:theme', theme)
  }, [theme])

  useEffect(() => {
    const onOnline = () => setOnline(true)
    const onOffline = () => setOnline(false)
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    return () => { window.removeEventListener('online', onOnline); window.removeEventListener('offline', onOffline) }
  }, [])

  const loadHistory = useCallback(async (activeUser: SessionUser) => {
    setHistoryLoading(true)
    try { setHistory(await listarRoteiros(activeUser)) }
    catch (error) { setNotice({ tone: 'warning', message: errorMessage(error) }) }
    finally { setHistoryLoading(false) }
  }, [])

  useEffect(() => {
    // A troca de identidade é a fonte externa que inicia a sincronização do histórico.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (user) void loadHistory(user)
    else { setHistory([]); setSelected(null) }
  }, [loadHistory, user])

  useEffect(() => {
    if (!user?.expiresAt) return
    const remaining = user.expiresAt - Date.now()
    const expire = () => {
      clearSession()
      setUser(null)
      setNotice({ tone: 'info', message: 'Sua sessão de visitante expirou. Entre novamente para continuar.' })
    }
    if (remaining <= 0) {
      expire()
      return
    }
    const timer = window.setTimeout(expire, remaining)
    return () => window.clearTimeout(timer)
  }, [user])

  const commitUser = (nextUser: SessionUser) => {
    saveSession(nextUser)
    setUser(nextUser)
    if (nextUser.modo === 'google') setSavedGoogleUser(nextUser)
    setNotice(null)
  }

  const authenticate = async (action: () => Promise<SessionUser>) => {
    setAuthLoading(true)
    try { commitUser(await action()) }
    catch (error) { setNotice({ tone: 'error', message: errorMessage(error) }) }
    finally { setAuthLoading(false) }
  }

  const logout = () => {
    planningController.current?.abort()
    clearSession()
    setUser(null)
    setGuide('')
    setNotice(null)
  }

  const locate = async () => {
    setLocating(true)
    try {
      setCurrentPosition(await getCurrentPosition())
      setNotice({ tone: 'info', message: 'Localização registrada. Vamos comparar a distância assim que a origem for localizada.' })
    } catch (error) { setNotice({ tone: 'warning', message: errorMessage(error) }) }
    finally { setLocating(false) }
  }

  const streamGuide = async (roteiro: Roteiro, input: PlanejamentoInput, activeUser: SessionUser, signal: AbortSignal) => {
    setStreaming(true)
    setGuide('')
    try {
      let content = ''
      for await (const event of transmitirGuia(roteiro, input, activeUser, signal)) {
        content += event.chunk
        setGuide(content)
        if (event.done) break
      }
    } catch (error) {
      if (!(error instanceof DOMException && error.name === 'AbortError')) setNotice({ tone: 'warning', message: `A rota está pronta, mas o guia não pôde ser transmitido. ${errorMessage(error)}` })
    } finally { setStreaming(false) }
  }

  const plan = async (input: PlanejamentoInput) => {
    if (!user || planning) return
    planningController.current?.abort()
    const controller = new AbortController()
    planningController.current = controller
    setPlanning(true)
    setNotice(null)
    try {
      const result = await planejarRoteiroComTelemetria(input, user, controller.signal)
      setSelected(result.data)
      setTelemetry(result.telemetry)
      setHistory((items) => [result.data, ...items.filter((item) => item.id !== result.data.id)])
      if (currentPosition && isFarFromOrigin(currentPosition, result.data.origem)) {
        setNotice({ tone: 'warning', message: 'Você parece estar a mais de 400 km da origem informada. Confirme a cidade antes de seguir.' })
      }
      void streamGuide(result.data, input, user, controller.signal)
    } catch (error) { setNotice({ tone: 'error', message: errorMessage(error) }) }
    finally { setPlanning(false) }
  }

  const remove = async (id: string) => {
    if (!user || !window.confirm('Excluir este roteiro do seu histórico?')) return
    try {
      await excluirRoteiro(id, user)
      setHistory((items) => items.filter((item) => item.id !== id))
      if (selected?.id === id) setSelected(null)
    } catch (error) { setNotice({ tone: 'error', message: errorMessage(error) }) }
  }

  const toggleVisit = async (attractionId: string, visited: boolean) => {
    if (!user || !selected) return
    try {
      const updated = await marcarParadaVisitada(selected.id, attractionId, visited, user)
      setSelected(updated)
      setHistory((items) => items.map((item) => item.id === updated.id ? updated : item))
    } catch (error) { setNotice({ tone: 'error', message: errorMessage(error) }) }
  }

  const openMaps = () => {
    if (!selected) return
    window.open(`https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(`${selected.origem.cidade}, ${selected.origem.uf}`)}&destination=${encodeURIComponent(`${selected.destino.cidade}, ${selected.destino.uf}`)}&travelmode=driving`, '_blank', 'noopener,noreferrer')
  }

  const shareWhatsApp = () => {
    if (!selected) return
    const text = `Minha viagem: ${selected.origem.cidade} → ${selected.destino.cidade} · ${Math.round(selected.distancia_km)} km · ${Math.round(selected.duracao_minutos / 60)}h.`
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener,noreferrer')
  }

  return (
    <div className="app-shell">
      <Header user={user} authLoading={authLoading} onVisitorLogin={() => void authenticate(loginVisitante)} onGoogleLogin={(credential) => void authenticate(() => loginGoogle(credential))} onLogout={logout} savedGoogleUser={savedGoogleUser} onRestoreGoogle={() => savedGoogleUser && commitUser(savedGoogleUser)} theme={theme} onToggleTheme={() => setTheme((value) => value === 'light' ? 'dark' : 'light')} />
      {!online && <div className="network-banner" role="status"><WifiOff size={16} /> Você está offline. O planejamento será liberado quando a conexão voltar.</div>}
      <main id="main" className="app-main">
        <section className="intro"><div><span className="intro-mark"><Navigation size={18} /> Brasil de ponta a ponta</span><h2>Sua viagem começa com um plano que faz sentido.</h2><p>Rota, autonomia, relevo, custos e um guia conciso — organizados para decidir com confiança.</p></div><div className="intro-route" aria-hidden="true"><span>Origem</span><i /><span>Destino</span></div></section>

        {notice && <div className={`notice notice-${notice.tone}`} role={notice.tone === 'error' ? 'alert' : 'status'}>{notice.tone === 'info' ? <Info /> : <AlertTriangle />}<span>{notice.message}</span><button type="button" onClick={() => setNotice(null)} aria-label="Fechar aviso">×</button></div>}

        {!user ? (
          <section className="signin-gate"><Map size={36} /><h1>Entre para abrir o planejador</h1><p>Use sua conta Google ou continue como visitante por até duas horas. Seus roteiros ficam separados por usuário.</p><button className="button button-primary" onClick={() => void authenticate(loginVisitante)} disabled={authLoading}>{authLoading ? 'Preparando sessão…' : 'Explorar como visitante'}</button></section>
        ) : (
          <div className="workspace">
            <div className="workspace-main">
              <RoteiroForm loading={planning} disabled={!online} onSubmit={(values) => void plan(values)} onLocate={() => void locate()} locating={locating} {...(currentPosition ? { currentPosition } : {})} />
              {planning && <section className="result-skeleton" aria-label="Calculando roteiro"><div /><span /><span /><span /></section>}
              {selected && !planning && <section className="result-panel" aria-labelledby="result-title">
                <div className="result-header"><div><span>Roteiro calculado</span><h2 id="result-title">{selected.origem.cidade} <i aria-hidden="true">→</i> {selected.destino.cidade}</h2></div><div className="result-actions"><button className="button button-secondary" type="button" onClick={openMaps}><ExternalLink size={16} /> Maps</button><button className="button button-secondary" type="button" onClick={shareWhatsApp}><MessageCircle size={16} /> WhatsApp</button><button className="button button-secondary" type="button" onClick={() => user && void baixarGpx(selected.id, user).catch((error) => setNotice({ tone: 'error', message: errorMessage(error) }))}><Download size={16} /> GPX</button></div></div>
                <MapaRota roteiro={selected} />
                <TelemetriaCard roteiro={selected} {...(telemetry ? { telemetry } : {})} user={user} />
                {selected.diagnosticos?.some((item) => item.status !== 'disponivel') && <div className="partial-warning"><AlertTriangle size={17} /> Alguns dados estão parciais: {selected.diagnosticos.filter((item) => item.status !== 'disponivel').map((item) => item.provedor).join(', ')}.</div>}
                <details className="elevation-details"><summary>Topografia e relevo</summary><dl><div><dt>Altitude máxima</dt><dd>{selected.altimetria?.altitude_maxima_m === undefined ? '—' : `${Math.round(selected.altimetria.altitude_maxima_m)} m`}</dd></div><div><dt>Subida / descida</dt><dd>+{Math.round(selected.altimetria?.ganho_m ?? 0)} m / −{Math.round(selected.altimetria?.perda_m ?? 0)} m</dd></div><div><dt>Impacto no consumo</dt><dd>{selected.altimetria?.impacto_consumo_percentual === undefined ? '—' : `${selected.altimetria.impacto_consumo_percentual > 0 ? '+' : ''}${selected.altimetria.impacto_consumo_percentual.toFixed(1)}%`}</dd></div></dl></details>
                <GuiaViajante roteiro={selected} text={guide || selected.guia || ''} streaming={streaming} onToggleVisit={(id, visited) => void toggleVisit(id, visited)} />
              </section>}
            </div>
            <HistoricoViagens items={history} loading={historyLoading} {...(selected ? { selectedId: selected.id } : {})} onSelect={(item) => { setSelected(item); setGuide(item.guia ?? ''); setTelemetry(undefined) }} onDelete={(id) => void remove(id)} />
          </div>
        )}
      </main>
      <footer className="footer"><span>Guia do Turista Inteligente · Unidade II</span><span>React 19 + FastAPI</span></footer>
    </div>
  )
}
