import { Bot, Check, CloudSun, LoaderCircle, Sparkles } from 'lucide-react'
import type { Roteiro } from '../types/roteiro'

interface GuiaViajanteProps {
  roteiro: Roteiro
  text: string
  streaming: boolean
  onToggleVisit: (id: string, visitado: boolean) => void
}

export function GuiaViajante({ roteiro, text, streaming, onToggleVisit }: GuiaViajanteProps) {
  return (
    <section className="guide-section" aria-labelledby="guide-title">
      <div className="weather-strip">
        <CloudSun size={24} />
        <div><strong>{roteiro.clima?.temperatura_c === undefined ? 'Clima temporariamente indisponível' : `${Math.round(roteiro.clima.temperatura_c)} °C em ${roteiro.destino.cidade}`}</strong><span>{roteiro.clima?.descricao ?? (roteiro.clima?.vento_kmh ? `Ventos de ${Math.round(roteiro.clima.vento_kmh)} km/h` : 'Planeje com uma margem para mudanças no tempo.')}</span></div>
      </div>
      <div className="guide-copy">
        <div className="section-heading compact"><span className="heading-icon"><Bot size={19} /></span><div><h2 id="guide-title">Guia do viajante</h2><p>Uma síntese objetiva, criada enquanto você acompanha.</p></div></div>
        <div className="stream-text" aria-live="polite" aria-busy={streaming}>
          {text ? <p>{text}</p> : <p className="muted">O guia começará assim que a rota estiver pronta.</p>}
          {streaming && <span className="streaming-label"><LoaderCircle size={15} /> Gerando recomendações…</span>}
        </div>
      </div>
      {roteiro.atrativos && roteiro.atrativos.length > 0 && <div className="attractions"><h3><Sparkles size={17} /> Atrativos e sabores locais</h3><ul>{roteiro.atrativos.map((item) => <li key={item.id}><div><strong>{item.nome}</strong>{item.descricao && <p>{item.descricao}</p>}</div><button className={item.visitado ? 'visited' : ''} type="button" onClick={() => onToggleVisit(item.id, !item.visitado)}><Check size={15} /> {item.visitado ? 'Visitado' : 'Marcar visita'}</button></li>)}</ul></div>}
    </section>
  )
}
