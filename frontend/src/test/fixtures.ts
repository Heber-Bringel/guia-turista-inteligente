import type { Roteiro } from '../types/roteiro'

export const roteiroFixture: Roteiro = {
  id: 'rota-1',
  criado_em: '2026-10-28T12:00:00Z',
  origem: { cidade: 'Recife', uf: 'PE', latitude: -8.05, longitude: -34.9 },
  destino: { cidade: 'Salvador', uf: 'BA', latitude: -12.97, longitude: -38.5 },
  distancia_km: 806,
  duracao_minutos: 690,
  geometria: { type: 'LineString', coordinates: [[-34.9, -8.05], [-38.5, -12.97]] },
  paradas: [],
}
