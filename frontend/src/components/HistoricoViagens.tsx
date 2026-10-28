import { Clock3, History, MapPin, Trash2 } from 'lucide-react'
import type { Roteiro } from '../types/roteiro'

interface HistoricoViagensProps {
  items: Roteiro[]
  loading: boolean
  selectedId?: string
  onSelect: (roteiro: Roteiro) => void
  onDelete: (id: string) => void
}

const shortDate = (date: string) => new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short' }).format(new Date(date))

export function HistoricoViagens({ items, loading, selectedId, onSelect, onDelete }: HistoricoViagensProps) {
  return (
    <aside className="history-panel" aria-labelledby="history-title">
      <div className="section-heading compact"><span className="heading-icon"><History size={19} /></span><div><h2 id="history-title">Viagens salvas</h2><p>Seu histórico acompanha a sessão.</p></div></div>
      {loading ? <div className="history-skeleton" aria-label="Carregando histórico"><span /><span /><span /></div> : items.length === 0 ? (
        <div className="empty-state"><MapPin size={24} /><strong>Nenhuma viagem ainda</strong><p>Seu primeiro roteiro aparecerá aqui depois do planejamento.</p></div>
      ) : (
        <ul className="history-list">{items.map((item) => <li key={item.id} className={item.id === selectedId ? 'selected' : ''}>
          <button type="button" className="history-select" onClick={() => onSelect(item)} aria-current={item.id === selectedId ? 'true' : undefined}>
            <strong>{item.origem.cidade} <span aria-hidden="true">→</span> {item.destino.cidade}</strong>
            <small><Clock3 size={13} /> {shortDate(item.criado_em)} · {Math.round(item.distancia_km)} km</small>
          </button>
          <button type="button" className="history-delete" onClick={() => onDelete(item.id)} aria-label={`Excluir roteiro para ${item.destino.cidade}`}><Trash2 size={16} /></button>
        </li>)}</ul>
      )}
    </aside>
  )
}
