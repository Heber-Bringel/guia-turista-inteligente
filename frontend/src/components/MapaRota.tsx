import { useEffect, useState } from 'react'
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import L, { type LatLngBoundsExpression } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { Roteiro } from '../types/roteiro'

interface MapaRotaProps { roteiro: Roteiro }

const markerIcon = L.divIcon({ className: 'route-marker', html: '<span></span>', iconSize: [18, 18], iconAnchor: [9, 9] })
const stopIcon = L.divIcon({ className: 'stop-marker', html: '<span></span>', iconSize: [14, 14], iconAnchor: [7, 7] })

function FitRoute({ bounds }: { bounds: LatLngBoundsExpression }) {
  const map = useMap()
  useEffect(() => { map.fitBounds(bounds, { padding: [28, 28] }) }, [bounds, map])
  return null
}

export function MapaRota({ roteiro }: MapaRotaProps) {
  const [selectedRouteKey, setSelectedRouteKey] = useState<string>('')

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

  return (
    <div className="map-section">
      {options.length > 1 && (
        <div className="route-tabs" role="tablist" aria-label="Opções de rota">
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
      <div className="map-wrap" aria-label={`Mapa da rota de ${roteiro.origem.cidade} para ${roteiro.destino.cidade}`}>
        <MapContainer bounds={bounds} scrollWheelZoom={false} className="route-map">
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {options.map((option, index) => index !== activeIndex && (
            <Polyline
              key={`alt-${option.key}`}
              positions={option.coordinates.map(([longitude, latitude]) => [latitude, longitude])}
              pathOptions={{ color: '#6d7f8b', weight: 3, dashArray: '7 8', opacity: 0.65 }}
            />
          ))}
          <Polyline positions={route} pathOptions={{ color: '#0877ad', weight: 5, opacity: 0.9 }} />
          <Marker position={[roteiro.origem.latitude, roteiro.origem.longitude]} icon={markerIcon}><Popup>Partida: {roteiro.origem.cidade}</Popup></Marker>
          <Marker position={[roteiro.destino.latitude, roteiro.destino.longitude]} icon={markerIcon}><Popup>Destino: {roteiro.destino.cidade}</Popup></Marker>
          {roteiro.paradas.map((stop, index) => <Marker key={stop.id ?? `${stop.latitude}-${stop.longitude}`} position={[stop.latitude, stop.longitude]} icon={stopIcon}><Popup>Parada {index + 1}: {stop.nome}{stop.estimada ? ' (estimada)' : ''}</Popup></Marker>)}
          <FitRoute bounds={bounds} />
        </MapContainer>
      </div>
    </div>
  )
}
