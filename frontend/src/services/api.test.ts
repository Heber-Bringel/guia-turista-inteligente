import { afterEach, describe, expect, it, vi } from 'vitest'
import { setCurrentLanguage } from '../i18n/language'
import type { SessionUser } from '../types/api'
import { roteiroFixture } from '../test/fixtures'
import { conversarRoteiro, despacharRoteiro, errorMessage, listarRoteiros, parseSseStream } from './api'

const encoder = new TextEncoder()

const mockUser: SessionUser = {
  id: 'usr_1',
  nome: 'Héber Bringel',
  email: 'heber@exemplo.com',
  modo: 'google',
  accessToken: 'token-demo',
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('parseSseStream', () => {
  it('preserva evento dividido entre pacotes e encerra em done', async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"chunk":"Olá, ","done":fal'))
        controller.enqueue(encoder.encode('se}\n\ndata: {"chunk":"viajante!","done":false}\r\n\r\n'))
        controller.enqueue(encoder.encode('data: {"chunk":"","done":true}\n\n'))
        controller.enqueue(encoder.encode('data: {"chunk":"duplicado","done":false}\n\n'))
        controller.close()
      },
    })

    const events = []
    for await (const event of parseSseStream(stream)) events.push(event)

    expect(events).toEqual([
      { chunk: 'Olá, ', done: false },
      { chunk: 'viajante!', done: false },
      { chunk: '', done: true },
    ])
  })

  it('combina múltiplas linhas data do mesmo evento', async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"chunk":"linha",\ndata: "done":false}\n\n'))
        controller.close()
      },
    })
    const events = []
    for await (const event of parseSseStream(stream)) events.push(event)
    expect(events[0]).toEqual({ chunk: 'linha', done: false })
  })
})

describe('API V3: Accept-Language, chat, despacho e higienização de erros', () => {
  it('propaga o cabeçalho Accept-Language ativo e faz fallback seguro para idioma inválido', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      new Response(JSON.stringify([]), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )

    setCurrentLanguage('en')
    await listarRoteiros(mockUser)
    const firstHeaders = fetchMock.mock.calls[0]?.[1]?.headers as Headers
    expect(firstHeaders.get('Accept-Language')).toBe('en')

    setCurrentLanguage('ar')
    expect(document.documentElement.dir).toBe('rtl')
    await listarRoteiros(mockUser)
    const secondHeaders = fetchMock.mock.calls[1]?.[1]?.headers as Headers
    expect(secondHeaders.get('Accept-Language')).toBe('ar')

    setCurrentLanguage('ja')
    await listarRoteiros(mockUser)
    const thirdHeaders = fetchMock.mock.calls[2]?.[1]?.headers as Headers
    expect(thirdHeaders.get('Accept-Language')).toBe('pt-BR')
    expect(document.documentElement.dir).toBe('ltr')
  })

  it('envia diálogo multi-turno para /roteiros/chat com Accept-Language', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          resposta: 'Visit Parque Nacional de Sete Cidades in the morning.',
          idioma: 'en',
          destino: 'Piripiri - PI',
          patrimonios_preservados: ['Parque Nacional de Sete Cidades'],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const response = await conversarRoteiro(
      {
        destino: 'Piripiri - PI',
        ritmo_viagem: 'tranquilo',
        acompanhantes: 'Família',
        preferencias_gastronomia: 'Culinária piauiense',
        mensagem: 'Quero conhecer Sete Cidades',
        historico: [],
      },
      mockUser,
      'en',
    )

    expect(response.patrimonios_preservados).toContain('Parque Nacional de Sete Cidades')
    const [url, init] = fetchMock.mock.calls[0] ?? []
    expect(String(url)).toMatch(/\/api\/v1\/roteiros\/chat$/)
    expect((init?.headers as Headers).get('Accept-Language')).toBe('en')
  })

  it('dispara despacho multicanal para /roteiros/despachar em e-mail e WhatsApp', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          status: 'agendado',
          protocolo: 'dsp_12345',
          canal: 'whatsapp',
          destinatario: '+5586999999999',
          idioma: 'pt-BR',
          mensagem: 'Seu roteiro está sendo enviado por WhatsApp.',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const result = await despacharRoteiro(
      {
        roteiro_id: roteiroFixture.id,
        canal: 'whatsapp',
        destinatario: '+5586999999999',
        nome_viajante: mockUser.nome,
        resumo_guia: 'Guia personalizado',
        roteiro: roteiroFixture,
      },
      mockUser,
      'pt-BR',
    )

    expect(result.status).toBe('agendado')
    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(/\/api\/v1\/roteiros\/despachar$/)
  })

  it('higieniza erros 500/503 sem expor stack trace ou detalhe técnico cru', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: 'Traceback (most recent call last): psycopg2.OperationalError at 10.0.0.1 trace_id=abc-123',
        }),
        { status: 500, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    await expect(listarRoteiros(mockUser, undefined, 'pt-BR')).rejects.toSatisfy((error: unknown) => {
      const msg = errorMessage(error, 'pt-BR')
      expect(msg).not.toMatch(/Traceback|psycopg2|trace_id|10\.0\.0\.1/i)
      expect(msg).toMatch(/tente novamente/i)
      return true
    })
  })
})
