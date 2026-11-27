import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Roteiro } from '../types/roteiro'
import { roteiroFixture } from '../test/fixtures'
import { TelemetriaCard } from './TelemetriaCard'

const roteiroCompleto: Roteiro = {
  ...roteiroFixture,
  clima: { temperatura_c: 31, descricao: 'Ensolarado' },
  altimetria: { ganho_m: 420 },
  custos: { total: 350.5, por_passageiro: 175.25, moeda: 'BRL' },
  diagnosticos: [
    { provedor: 'rota', status: 'disponivel', mensagem: 'OSRM 120ms' },
    { provedor: 'clima', status: 'indisponivel', mensagem: 'Timeout interno' },
  ],
}

describe('TelemetriaCard (Higienização pública V3)', () => {
  it('exibe apenas indicadores úteis ao viajante e oculta métricas técnicas internas', () => {
    const { container } = render(<TelemetriaCard roteiro={roteiroCompleto} />)

    expect(screen.getByText('806 km')).toBeInTheDocument()
    expect(screen.getByText('11h 30min')).toBeInTheDocument()
    expect(screen.getByText('31 °C')).toBeInTheDocument()
    expect(screen.getByText('420 m')).toBeInTheDocument()

    const text = container.textContent ?? ''
    expect(text).not.toMatch(/provedores ativos/i)
    expect(text).not.toMatch(/Latência da API/i)
    expect(text).not.toMatch(/Tempo no navegador/i)
    expect(text).not.toMatch(/X-Request-ID|X-Process-Time|\bID\s+[a-f0-9]{6,}/i)
    expect(text).not.toMatch(/\b\d+\s*ms\b/i)
  })
})
