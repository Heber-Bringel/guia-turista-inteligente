import { CloudSun, Gauge, Leaf, Mountain, Timer, Users } from 'lucide-react'
import type { RequestTelemetry, SessionUser } from '../types/api'
import type { Roteiro } from '../types/roteiro'

interface TelemetriaCardProps { roteiro: Roteiro; telemetry?: RequestTelemetry; user?: SessionUser }

const formatCurrency = (value?: number) => value === undefined ? '—' : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
const formatDuration = (minutes: number) => `${Math.floor(minutes / 60)}h ${Math.round(minutes % 60)}min`

export function TelemetriaCard({ roteiro, telemetry, user }: TelemetriaCardProps) {
  const providersUp = roteiro.diagnosticos?.filter((item) => item.status === 'disponivel').length
  const providersTotal = roteiro.diagnosticos?.length
  const metrics = [
    { icon: <Gauge />, label: 'Distância', value: `${Math.round(roteiro.distancia_km).toLocaleString('pt-BR')} km` },
    { icon: <Timer />, label: 'Tempo estimado', value: formatDuration(roteiro.duracao_minutos) },
    { icon: <CloudSun />, label: 'Clima no destino', value: roteiro.clima?.temperatura_c === undefined ? 'Indisponível' : `${Math.round(roteiro.clima.temperatura_c)} °C` },
    { icon: <Mountain />, label: 'Ganho de elevação', value: roteiro.altimetria?.ganho_m === undefined ? 'Indisponível' : `${Math.round(roteiro.altimetria.ganho_m)} m` },
    { icon: <Leaf />, label: 'Custo total', value: formatCurrency(roteiro.custos?.total) },
    { icon: <Users />, label: 'Por viajante', value: formatCurrency(roteiro.custos?.por_passageiro) },
    ...(telemetry ? [
      { icon: <Gauge />, label: 'Latência da API', value: telemetry.processTimeMs === undefined ? 'Não informada' : `${Math.round(telemetry.processTimeMs)} ms` },
      { icon: <Timer />, label: 'Tempo no navegador', value: `${Math.round(telemetry.totalTimeMs)} ms` },
    ] : []),
  ]

  return <><div className="telemetry-line"><span>{user?.modo === 'google' ? 'Google conectado' : 'Visitante temporário'}</span>{providersTotal ? <span>{providersUp}/{providersTotal} provedores ativos</span> : null}{telemetry?.requestId ? <span title={telemetry.requestId}>ID {telemetry.requestId.slice(0, 8)}</span> : null}</div><div className="metrics" aria-label="Resumo da viagem">{metrics.map((metric) => <div className="metric" key={metric.label}><span>{metric.icon}</span><div><small>{metric.label}</small><strong>{metric.value}</strong></div></div>)}</div></>
}
