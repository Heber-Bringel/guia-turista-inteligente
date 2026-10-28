import { useEffect } from 'react'
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
  const route = roteiro.geometria.coordinates.map(([longitude, latitude]) => [latitude, longitude] as [number, number])
  const bounds: LatLngBoundsExpression = route.length > 1
    ? route
    : [[roteiro.origem.latitude, roteiro.origem.longitude], [roteiro.destino.latitude, roteiro.destino.longitude]]

  return (
    <div className="map-wrap" aria-label={`Mapa da rota de ${roteiro.origem.cidade} para ${roteiro.destino.cidade}`}>
      <MapContainer bounds={bounds} scrollWheelZoom={false} className="route-map">
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <Polyline positions={route} pathOptions={{ color: '#0877ad', weight: 5, opacity: 0.9 }} />
        {roteiro.alternativas?.map((alternative, index) => <Polyline key={index} positions={alternative.coordinates.map(([longitude, latitude]) => [latitude, longitude])} pathOptions={{ color: '#6d7f8b', weight: 3, dashArray: '7 8', opacity: 0.65 }} />)}
        <Marker position={[roteiro.origem.latitude, roteiro.origem.longitude]} icon={markerIcon}><Popup>Partida: {roteiro.origem.cidade}</Popup></Marker>
        <Marker position={[roteiro.destino.latitude, roteiro.destino.longitude]} icon={markerIcon}><Popup>Destino: {roteiro.destino.cidade}</Popup></Marker>
        {roteiro.paradas.map((stop, index) => <Marker key={stop.id ?? `${stop.latitude}-${stop.longitude}`} position={[stop.latitude, stop.longitude]} icon={stopIcon}><Popup>Parada {index + 1}: {stop.nome}{stop.estimada ? ' (estimada)' : ''}</Popup></Marker>)}
        <FitRoute bounds={bounds} />
      </MapContainer>
    </div>
  )
}
