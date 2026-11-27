import { Bot, Check, CloudSun, LoaderCircle, Sparkles } from 'lucide-react'
import { getTranslations } from '../i18n/language'
import type { SupportedLanguage } from '../types/api'
import type { Roteiro } from '../types/roteiro'

interface GuiaViajanteProps {
  roteiro: Roteiro
  text: string
  streaming: boolean
  language?: SupportedLanguage
  onToggleVisit: (id: string, visitado: boolean) => void
}

export function GuiaViajante({
  roteiro,
  text,
  streaming,
  language = 'pt-BR',
  onToggleVisit,
}: GuiaViajanteProps) {
  const t = getTranslations(language)

  return (
    <section className="guide-section" aria-labelledby="guide-title">
      <div className="weather-strip">
        <CloudSun size={24} />
        <div>
          <strong>
            {roteiro.clima?.temperatura_c === undefined
              ? t.weatherUnavailable
              : `${Math.round(roteiro.clima.temperatura_c)} °C · ${roteiro.destino.cidade}`}
          </strong>
          <span>
            {roteiro.clima?.descricao ??
              (roteiro.clima?.vento_kmh ? `${Math.round(roteiro.clima.vento_kmh)} km/h` : t.weatherFallbackHint)}
          </span>
        </div>
      </div>

      <div className="guide-copy">
        <div className="section-heading compact">
          <span className="heading-icon"><Bot size={19} /></span>
          <div>
            <h2 id="guide-title">{t.guideTitle}</h2>
            <p>{t.guideSubtitle}</p>
          </div>
        </div>
        <div className="stream-text" aria-live="polite" aria-busy={streaming}>
          {text ? <p>{text}</p> : <p className="muted">{t.guidePending}</p>}
          {streaming && (
            <span className="streaming-label">
              <LoaderCircle size={15} /> {t.guideStreaming}
            </span>
          )}
        </div>
      </div>

      {roteiro.atrativos && roteiro.atrativos.length > 0 && (
        <div className="attractions">
          <h3><Sparkles size={17} /> {t.attractionsTitle}</h3>
          <ul>
            {roteiro.atrativos.map((item) => (
              <li key={item.id}>
                <div>
                  <strong>{item.nome}</strong>
                  {item.descricao && <p>{item.descricao}</p>}
                </div>
                <button
                  className={item.visitado ? 'visited' : ''}
                  type="button"
                  onClick={() => onToggleVisit(item.id, !item.visitado)}
                >
                  <Check size={15} /> {item.visitado ? t.visited : t.markVisited}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
