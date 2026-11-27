import { Clock3, History, MapPin, Trash2 } from 'lucide-react'
import { getTranslations } from '../i18n/language'
import type { SupportedLanguage } from '../types/api'
import type { Roteiro } from '../types/roteiro'

interface HistoricoViagensProps {
  items: Roteiro[]
  loading: boolean
  selectedId?: string
  language?: SupportedLanguage
  onSelect: (roteiro: Roteiro) => void
  onDelete: (id: string) => void
}

const shortDate = (date: string, locale: string) =>
  new Intl.DateTimeFormat(locale, { day: '2-digit', month: 'short' }).format(new Date(date))

export function HistoricoViagens({
  items,
  loading,
  selectedId,
  language = 'pt-BR',
  onSelect,
  onDelete,
}: HistoricoViagensProps) {
  const t = getTranslations(language)

  return (
    <aside className="history-panel" aria-labelledby="history-title">
      <div className="section-heading compact">
        <span className="heading-icon"><History size={19} /></span>
        <div>
          <h2 id="history-title">{t.historyTitle}</h2>
          <p>{t.historySubtitle}</p>
        </div>
      </div>

      {loading ? (
        <div className="history-skeleton" aria-label="Carregando histórico"><span /><span /><span /></div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <MapPin size={24} />
          <strong>{t.historyEmptyTitle}</strong>
          <p>{t.historyEmptyBody}</p>
        </div>
      ) : (
        <ul className="history-list">
          {items.map((item) => (
            <li key={item.id} className={item.id === selectedId ? 'selected' : ''}>
              <button
                type="button"
                className="history-select"
                onClick={() => onSelect(item)}
                aria-current={item.id === selectedId ? 'true' : undefined}
              >
                <strong>{item.origem.cidade} <span aria-hidden="true">→</span> {item.destino.cidade}</strong>
                <small><Clock3 size={13} /> {shortDate(item.criado_em, language)} · {Math.round(item.distancia_km)} km</small>
              </button>
              <button
                type="button"
                className="history-delete"
                onClick={() => onDelete(item.id)}
                aria-label={`Excluir roteiro para ${item.destino.cidade}`}
              >
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
