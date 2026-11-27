import { useState, type ReactNode } from 'react'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Roteiro } from '../types/roteiro'
import { MapaRota } from './MapaRota'

const markerPropsCaptured: Array<Record<string, unknown>> = []

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div data-testid="leaflet-map">{children}</div>,
  TileLayer: () => null,
  Polyline: () => null,
  useMap: () => ({ fitBounds: vi.fn() }),
  Popup: ({ children }: { children: ReactNode }) => <div role="dialog">{children}</div>,
  Marker: (props: { children?: ReactNode; title?: string; eventHandlers?: Record<string, unknown> }) => {
    markerPropsCaptured.push(props as Record<string, unknown>)
    const [open, setOpen] = useState(false)
    return (
      <div>
        <button type="button" onClick={() => setOpen((current) => !current)}>
          {props.title ?? 'Marcador'}
        </button>
        {open ? props.children : null}
      </div>
    )
  },
}))

const roteiroAnpBr343: Roteiro = {
  id: 'rot-br343',
  criado_em: '2026-11-27T12:00:00Z',
  origem: { cidade: 'Teresina', uf: 'PI', latitude: -5.089, longitude: -42.801 },
  destino: { cidade: 'Parnaíba', uf: 'PI', latitude: -2.905, longitude: -41.776 },
  distancia_km: 338,
  duracao_minutos: 285,
  geometria: { type: 'LineString', coordinates: [[-42.801, -5.089], [-41.778, -4.273], [-41.776, -2.905]] },
  paradas: [
    {
      id: 'posto-anp-piripiri',
      nome: 'Posto Piripiri BR-343 (km 160)',
      latitude: -4.273,
      longitude: -41.778,
      distancia_origem_km: 160,
      estimada: false,
      cnpj: '07.456.789/0001-90',
      razao_social: 'Auto Posto Caldeirão da BR-343 Ltda',
      avaliacao: 4.8,
      tempo_autorizacao_anp: '14 anos',
      combustiveis: ['Gasolina Comum', 'Etanol', 'Diesel S10'],
      ranking_score: 9.4,
      rodovia: 'BR-343',
      municipio: 'Piripiri',
      uf: 'PI',
    },
  ],
}

describe('MapaRota (Pop-up regulatório ANP)', () => {
  it('abre o pop-up ANP exclusivamente por clique no marcador e exibe os 5 atributos regulatórios', async () => {
    markerPropsCaptured.length = 0
    const user = userEvent.setup()
    render(<MapaRota roteiro={roteiroAnpBr343} />)

    // Nenhum marcador registra handlers automáticos de hover/mouseover.
    for (const captured of markerPropsCaptured) {
      expect(captured.eventHandlers).toBeUndefined()
    }

    // Antes do clique, o pop-up regulatório não está visível.
    expect(screen.queryByText('07.456.789/0001-90')).not.toBeInTheDocument()
    expect(screen.queryByText('14 anos')).not.toBeInTheDocument()

    // Ao clicar no marcador do posto na BR-343, o pop-up abre com todos os atributos ANP.
    await user.click(screen.getByRole('button', { name: 'Auto Posto Caldeirão da BR-343 Ltda' }))

    const popup = screen.getByRole('dialog')
    expect(within(popup).getByText('Auto Posto Caldeirão da BR-343 Ltda')).toBeInTheDocument()
    expect(within(popup).getByText('07.456.789/0001-90')).toBeInTheDocument()
    expect(within(popup).getByText('4.8 / 5.0')).toBeInTheDocument()
    expect(within(popup).getByText('14 anos')).toBeInTheDocument()
    expect(within(popup).getByText('Gasolina Comum')).toBeInTheDocument()
    expect(within(popup).getByText('Etanol')).toBeInTheDocument()
    expect(within(popup).getByText('Diesel S10')).toBeInTheDocument()
  })
})
