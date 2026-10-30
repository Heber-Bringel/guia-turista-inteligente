import { describe, expect, it } from 'vitest'
import { findNearestCity, haversineDistanceKm, isFarFromOrigin, suggestDestinationsBeyondRadius } from './geolocation'

describe('haversineDistanceKm', () => {
  it('calcula a distância geodésica em quilômetros', () => {
    const distance = haversineDistanceKm(
      { latitude: -8.0476, longitude: -34.877 },
      { latitude: -12.9777, longitude: -38.5016 },
    )
    expect(distance).toBeGreaterThan(670)
    expect(distance).toBeLessThan(690)
  })

  it('aplica a regra de alerta acima de 400 km', () => {
    expect(isFarFromOrigin({ latitude: -8.0476, longitude: -34.877 }, { latitude: -12.9777, longitude: -38.5016 })).toBe(true)
    expect(isFarFromOrigin({ latitude: -8.0476, longitude: -34.877 }, { latitude: -8.05, longitude: -34.9 })).toBe(false)
  })

  it('encontra a cidade de referência mais próxima e sugere destinos > 400 km', () => {
    const posTeresina = { latitude: -5.09, longitude: -42.8 }
    expect(findNearestCity(posTeresina)).toEqual(expect.objectContaining({ cidade: 'Teresina', uf: 'PI' }))

    const sugestoes = suggestDestinationsBeyondRadius(posTeresina, 400, 4)
    expect(sugestoes).toHaveLength(4)
    expect(sugestoes.every((item) => item.distancia_km > 400)).toBe(true)
  })
})
