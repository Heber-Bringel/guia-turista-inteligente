import { CloudSun, Gauge, Leaf, Mountain, Timer, Users } from 'lucide-react'
import { getTranslations } from '../i18n/language'
import type { SupportedLanguage } from '../types/api'
import type { Roteiro } from '../types/roteiro'

interface TelemetriaCardProps {
  roteiro: Roteiro
  language?: SupportedLanguage
}

const formatCurrency = (value: number | undefined, locale: string) =>
  value === undefined ? '—' : new Intl.NumberFormat(locale, { style: 'currency', currency: 'BRL' }).format(value)

const formatDuration = (minutes: number) => `${Math.floor(minutes / 60)}h ${Math.round(minutes % 60)}min`

export function TelemetriaCard({ roteiro, language = 'pt-BR' }: TelemetriaCardProps) {
  const t = getTranslations(language)
  const metrics = [
    { icon: <Gauge />, label: t.metricDistance, value: `${Math.round(roteiro.distancia_km).toLocaleString(language)} km` },
    { icon: <Timer />, label: t.metricDuration, value: formatDuration(roteiro.duracao_minutos) },
    {
      icon: <CloudSun />,
      label: t.metricWeather,
      value: roteiro.clima?.temperatura_c === undefined ? t.unavailable : `${Math.round(roteiro.clima.temperatura_c)} °C`,
    },
    {
      icon: <Mountain />,
      label: t.metricElevation,
      value: roteiro.altimetria?.ganho_m === undefined ? t.unavailable : `${Math.round(roteiro.altimetria.ganho_m)} m`,
    },
    { icon: <Leaf />, label: t.metricTotalCost, value: formatCurrency(roteiro.custos?.total, language) },
    { icon: <Users />, label: t.metricPerTraveler, value: formatCurrency(roteiro.custos?.por_passageiro, language) },
  ]

  return (
    <div className="metrics" aria-label={t.calculatedRoute}>
      {metrics.map((metric) => (
        <div className="metric" key={metric.label}>
          <span>{metric.icon}</span>
          <div>
            <small>{metric.label}</small>
            <strong>{metric.value}</strong>
          </div>
        </div>
      ))}
    </div>
  )
}
