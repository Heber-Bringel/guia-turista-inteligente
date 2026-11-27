import type { ReactNode } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { saveSession } from './services/session'
import type { Roteiro } from './types/roteiro'
import { roteiroFixture } from './test/fixtures'
import App from './App'

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div data-testid="leaflet-map">{children}</div>,
  TileLayer: () => null,
  Polyline: () => null,
  Marker: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Popup: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  useMap: () => ({ fitBounds: vi.fn() }),
}))

const roteiroComDiagnosticoFalho: Roteiro = {
  ...roteiroFixture,
  diagnosticos: [
    { provedor: 'clima', status: 'indisponivel', mensagem: 'Open-Meteo HTTP 503' },
    { provedor: 'gemini', status: 'parcial', mensagem: 'Fallback interno' },
  ],
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('App V3 (higienização, entrega multicanal e i18n RTL)', () => {
  it('substitui GPX por E-mail/WhatsApp, oculta provedores internos e aplica i18n/RTL', async () => {
    const user = userEvent.setup()
    saveSession({ id: 'usr_v3', nome: 'Héber Bringel', email: 'heber@exemplo.com', modo: 'google' })

    vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      new Response(JSON.stringify([roteiroComDiagnosticoFalho]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(<App />)

    // Seleciona o roteiro no histórico
    await user.click(await screen.findByRole('button', { name: /Recife.*Salvador/i }))

    // Botão manual GPX removido; botões multicanal presentes
    expect(screen.queryByRole('button', { name: /gpx/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /enviar por e-mail/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /enviar por whatsapp/i })).toBeInTheDocument()

    // Nenhum alerta parcial ou nome de provedor técnico na tela
    expect(screen.queryByText(/alguns dados estão parciais/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/provedores ativos/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Open-Meteo/i)).not.toBeInTheDocument()

    // Trocar idioma para Árabe ativa dir="rtl" e lang="ar"
    const langSelect = screen.getByLabelText(/idioma/i)
    await user.selectOptions(langSelect, 'ar')
    expect(document.documentElement.lang).toBe('ar')
    expect(document.documentElement.dir).toBe('rtl')

    // Trocar idioma para Inglês restaura ltr e traduz interface
    await user.selectOptions(langSelect, 'en')
    expect(document.documentElement.lang).toBe('en')
    expect(document.documentElement.dir).toBe('ltr')
    expect(screen.getByRole('button', { name: /send via email/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send via whatsapp/i })).toBeInTheDocument()
  })
})
