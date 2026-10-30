import type { Coordenada, Uf } from '../types/roteiro'

const EARTH_RADIUS_KM = 6371.0088

const toRadians = (degrees: number): number => degrees * (Math.PI / 180)

export interface DestinoReferencia extends Coordenada {
  cidade: string
  uf: Uf
}

export const CAPITAIS_BRASIL: readonly DestinoReferencia[] = [
  { cidade: 'Teresina', uf: 'PI', latitude: -5.0892, longitude: -42.8019 },
  { cidade: 'Fortaleza', uf: 'CE', latitude: -3.7172, longitude: -38.5431 },
  { cidade: 'São Luís', uf: 'MA', latitude: -2.5307, longitude: -44.3068 },
  { cidade: 'Natal', uf: 'RN', latitude: -5.7945, longitude: -35.211 },
  { cidade: 'Recife', uf: 'PE', latitude: -8.0476, longitude: -34.877 },
  { cidade: 'Salvador', uf: 'BA', latitude: -12.9777, longitude: -38.5016 },
  { cidade: 'João Pessoa', uf: 'PB', latitude: -7.1195, longitude: -34.845 },
  { cidade: 'Maceió', uf: 'AL', latitude: -9.6658, longitude: -35.735 },
  { cidade: 'Aracaju', uf: 'SE', latitude: -10.9472, longitude: -37.0731 },
  { cidade: 'Brasília', uf: 'DF', latitude: -15.7801, longitude: -47.9292 },
  { cidade: 'Goiânia', uf: 'GO', latitude: -16.6869, longitude: -49.2648 },
  { cidade: 'Belo Horizonte', uf: 'MG', latitude: -19.9167, longitude: -43.9345 },
  { cidade: 'São Paulo', uf: 'SP', latitude: -23.5505, longitude: -46.6333 },
  { cidade: 'Rio de Janeiro', uf: 'RJ', latitude: -22.9068, longitude: -43.1729 },
  { cidade: 'Curitiba', uf: 'PR', latitude: -25.4284, longitude: -49.2733 },
  { cidade: 'Florianópolis', uf: 'SC', latitude: -27.5954, longitude: -48.548 },
  { cidade: 'Porto Alegre', uf: 'RS', latitude: -30.0346, longitude: -51.2177 },
  { cidade: 'Belém', uf: 'PA', latitude: -1.4558, longitude: -48.4902 },
  { cidade: 'Palmas', uf: 'TO', latitude: -10.184, longitude: -48.3336 },
]

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

export function findNearestCity(current: Coordenada): DestinoReferencia {
  let nearest = CAPITAIS_BRASIL[0]!
  let minDistance = Infinity
  for (const city of CAPITAIS_BRASIL) {
    const dist = haversineDistanceKm(current, city)
    if (dist < minDistance) {
      minDistance = dist
      nearest = city
    }
  }
  return nearest
}

export function suggestDestinationsBeyondRadius(
  current: Coordenada,
  minDistanceKm = 400,
  limit = 4,
): Array<DestinoReferencia & { distancia_km: number }> {
  return CAPITAIS_BRASIL
    .map((city) => ({ ...city, distancia_km: Math.round(haversineDistanceKm(current, city)) }))
    .filter((city) => city.distancia_km > minDistanceKm)
    .sort((a, b) => a.distancia_km - b.distancia_km)
    .slice(0, limit)
}
