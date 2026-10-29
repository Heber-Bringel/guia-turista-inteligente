import type { Coordenada } from '../types/roteiro'

const EARTH_RADIUS_KM = 6371.0088

const toRadians = (degrees: number): number => degrees * (Math.PI / 180)

export function haversineDistanceKm(from: Coordenada, to: Coordenada): number {
  const latitudeDelta = toRadians(to.latitude - from.latitude)
  const longitudeDelta = toRadians(to.longitude - from.longitude)
  const fromLatitude = toRadians(from.latitude)
  const toLatitude = toRadians(to.latitude)

  const haversine =
    Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(fromLatitude) * Math.cos(toLatitude) * Math.sin(longitudeDelta / 2) ** 2

  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(haversine))
}

export function getCurrentPosition(): Promise<Coordenada> {
  if (!('geolocation' in navigator)) {
    return Promise.reject(new Error('Geolocalização não disponível neste navegador.'))
  }

  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ latitude: coords.latitude, longitude: coords.longitude }),
      () => reject(new Error('Não foi possível acessar sua localização.')),
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 300_000 },
    )
  })
}

export function isFarFromOrigin(current: Coordenada, origin: Coordenada, thresholdKm = 400): boolean {
  return haversineDistanceKm(current, origin) > thresholdKm
}
