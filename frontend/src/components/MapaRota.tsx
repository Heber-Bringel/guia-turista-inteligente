import { useEffect, useState } from 'react'
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import L, { type LatLngBoundsExpression } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Fuel, ShieldCheck, Star } from 'lucide-react'
import { getTranslations } from '../i18n/language'
import type { SupportedLanguage } from '../types/api'
import type { Parada, Roteiro } from '../types/roteiro'

interface MapaRotaProps {
  roteiro: Roteiro
  language?: SupportedLanguage
}

const markerIcon = L.divIcon({
  className: 'route-marker',
  html: '<span></span>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

const stopIcon = L.divIcon({
  className: 'stop-marker',
  html: '<span></span>',
  iconSize: [14, 14],
  iconAnchor: [7, 7],
})

const anpMarkerIcon = L.divIcon({
  className: 'anp-marker',
  html: '<span></span>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

function hasAnpData(stop: Parada): boolean {
  return Boolean(
    stop.cnpj ||
    stop.razao_social ||
    stop.tempo_autorizacao_anp !== undefined ||
    stop.avaliacao !== undefined ||
    (stop.combustiveis && stop.combustiveis.length > 0),
  )
}

function formatAuthTime(value: string | number | undefined, yearsSuffix: string, fallback: string): string {
  if (value === undefined || value === '') return fallback
  if (typeof value === 'number') return `${value} ${yearsSuffix}`
  return value
}

function FitRoute({ bounds }: { bounds: LatLngBoundsExpression }) {
  const map = useMap()
  useEffect(() => {
    map.fitBounds(bounds, { padding: [28, 28] })
  }, [bounds, map])
  return null
}

export function MapaRota({ roteiro, language = 'pt-BR' }: MapaRotaProps) {
  const [selectedRouteKey, setSelectedRouteKey] = useState<string>('')
  const t = getTranslations(language)

  const options = [
    {
      key: `${roteiro.id}-0`,
      nome: 'Sugestão 01 (Rota Principal)',
      distancia_km: roteiro.distancia_km,
      duracao_minutos: roteiro.duracao_minutos,
      coordinates: roteiro.geometria.coordinates,
    },
    ...(roteiro.alternativas ?? []).map((alt, idx) => ({
      key: `${roteiro.id}-${idx + 1}`,
      nome: alt.nome ?? `Sugestão 0${idx + 2} (Alternativa)`,
      distancia_km: alt.distancia_km ?? roteiro.distancia_km,
      duracao_minutos: alt.duracao_minutos ?? roteiro.duracao_minutos,
      coordinates: alt.coordinates,
    })),
  ]

  const activeIndex = Math.max(0, options.findIndex((o) => o.key === selectedRouteKey))
  const activeOption = options[activeIndex] ?? options[0]!
  const route = activeOption.coordinates.map(([longitude, latitude]) => [latitude, longitude] as [number, number])
  const bounds: LatLngBoundsExpression = route.length > 1
    ? route
    : [[roteiro.origem.latitude, roteiro.origem.longitude], [roteiro.destino.latitude, roteiro.destino.longitude]]
  const hasAnpStops = roteiro.paradas.some(hasAnpData)

  return (
    <div className="map-section">
      {options.length > 1 && (
        <div className="route-tabs" role="tablist" aria-label={t.mapRouteOptions}>
          {options.map((option, index) => (
            <button
              key={option.key}
              type="button"
              role="tab"
              aria-selected={activeIndex === index}
              className={`route-tab ${activeIndex === index ? 'active' : ''}`}
              onClick={() => setSelectedRouteKey(option.key)}
            >
              <strong>{option.nome}</strong>
              <small>{Math.round(option.distancia_km)} km · {Math.floor(option.duracao_minutos / 60)}h {Math.round(option.duracao_minutos % 60)}min</small>
            </button>
          ))}
        </div>
      )}
      {hasAnpStops && (
        <div className="map-hint">
          <Fuel size={15} aria-hidden="true" />
          <span>{t.mapHintAnp}</span>
        </div>
      )}
      <div className="map-wrap" aria-label={`Mapa da rota de ${roteiro.origem.cidade} para ${roteiro.destino.cidade}`}>
        <MapContainer bounds={bounds} scrollWheelZoom={false} className="route-map">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {options.map((option, index) => index !== activeIndex && (
            <Polyline
              key={`alt-${option.key}`}
              positions={option.coordinates.map(([longitude, latitude]) => [latitude, longitude])}
              pathOptions={{ color: '#6d7f8b', weight: 3, dashArray: '7 8', opacity: 0.65 }}
            />
          ))}
          <Polyline positions={route} pathOptions={{ color: '#0877ad', weight: 5, opacity: 0.9 }} />
          <Marker position={[roteiro.origem.latitude, roteiro.origem.longitude]} icon={markerIcon}>
            <Popup>{t.mapDeparture}: {roteiro.origem.cidade}</Popup>
          </Marker>
          <Marker position={[roteiro.destino.latitude, roteiro.destino.longitude]} icon={markerIcon}>
            <Popup>{t.mapDestination}: {roteiro.destino.cidade}</Popup>
          </Marker>
          {roteiro.paradas.map((stop, index) => {
            const regulatory = hasAnpData(stop)
            const stopKey = stop.id ?? `${stop.latitude}-${stop.longitude}-${index}`
            // Pop-up do Leaflet é vinculado diretamente ao Marker e abre exclusivamente por clique.
            return (
              <Marker
                key={stopKey}
                position={[stop.latitude, stop.longitude]}
                icon={regulatory ? anpMarkerIcon : stopIcon}
                title={stop.razao_social ?? stop.nome}
              >
                <Popup>
                  {regulatory ? (
                    <div className="anp-popup">
                      <div className="anp-popup-header">
                        <span className="anp-badge">
                          <ShieldCheck size={13} aria-hidden="true" /> {t.anpBadge}
                        </span>
                        {stop.ranking_score !== undefined && (
                          <span className="anp-rank">
                            {t.anpRanking}: {stop.ranking_score.toFixed(1)}
                          </span>
                        )}
                      </div>
                      <strong className="anp-title">{stop.nome}</strong>
                      {(stop.rodovia || stop.municipio) && (
                        <p className="anp-location">
                          {[stop.rodovia, stop.municipio, stop.uf].filter(Boolean).join(' · ')}
                        </p>
                      )}
                      <dl className="anp-details">
                        <div>
                          <dt>{t.anpCorporateName}</dt>
                          <dd>{stop.razao_social ?? stop.nome}</dd>
                        </div>
                        <div>
                          <dt>{t.anpCnpj}</dt>
                          <dd>{stop.cnpj ?? t.notInformed}</dd>
                        </div>
                        <div>
                          <dt>{t.anpRating}</dt>
                          <dd className="anp-rating">
                            <Star size={12} aria-hidden="true" />
                            {stop.avaliacao !== undefined ? `${stop.avaliacao.toFixed(1)} / 5.0` : t.notInformed}
                          </dd>
                        </div>
                        <div>
                          <dt>{t.anpAuthTime}</dt>
                          <dd>{formatAuthTime(stop.tempo_autorizacao_anp, t.yearsSuffix, t.notInformed)}</dd>
                        </div>
                      </dl>
                      <div className="anp-fuels">
                        <span>{t.anpFuels}</span>
                        {stop.combustiveis && stop.combustiveis.length > 0 ? (
                          <ul>
                            {stop.combustiveis.map((fuel) => (
                              <li key={fuel}>{fuel}</li>
                            ))}
                          </ul>
                        ) : (
                          <small>{t.notInformed}</small>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="anp-popup">
                      <strong className="anp-title">{stop.nome}</strong>
                      {stop.estimada && <p className="anp-location">{t.anpEstimatedStop}</p>}
                    </div>
                  )}
                </Popup>
              </Marker>
            )
          })}
          <FitRoute bounds={bounds} />
        </MapContainer>
      </div>
    </div>
  )
}
