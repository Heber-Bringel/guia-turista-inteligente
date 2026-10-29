import { describe, expect, it } from 'vitest'
import { haversineDistanceKm, isFarFromOrigin } from './geolocation'

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
})
