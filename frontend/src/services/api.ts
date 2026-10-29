import { ApiError, type ApiErrorBody, type ApiResult, type AuthResponse, type SessionUser, type StreamGuiaEvent } from '../types/api'
import type { PlanejamentoInput, Roteiro } from '../types/roteiro'

const API_BASE_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') || '/api/v1'

export const endpoints = {
  visitante: '/auth/visitante',
  google: '/auth/google',
  planejar: '/roteiros/planejar',
  mapa: '/roteiros/mapa-rota',
  historico: '/roteiros/minhas-viagens',
  roteiro: (id: string) => `/roteiros/${encodeURIComponent(id)}`,
  visita: (roteiroId: string) => `/roteiros/${encodeURIComponent(roteiroId)}/visitas`,
  stream: '/roteiros/stream-guia',
  gpx: '/roteiros/exportar/gpx',
} as const

const friendlyMessages: Record<number, string> = {
  401: 'Sua sessão expirou. Entre novamente para continuar.',
  409: 'Este roteiro já está sendo calculado. Aguarde a conclusão.',
  422: 'Revise os campos destacados e tente novamente.',
  503: 'Um serviço essencial está indisponível. Tente novamente em instantes.',
}

function headersFor(user: SessionUser | null, hasBody: boolean): Headers {
  const headers = new Headers({ Accept: 'application/json' })
  if (hasBody) headers.set('Content-Type', 'application/json')
  if (user?.accessToken) headers.set('Authorization', `Bearer ${user.accessToken}`)
  if (user?.id) headers.set('X-User-Id', user.id)
  return headers
}

async function parseError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody | undefined
  try {
    body = await response.json() as ApiErrorBody
  } catch {
    body = undefined
  }

  const detail = typeof body?.detail === 'string' ? body.detail : body?.message
  return new ApiError(response.status, detail || friendlyMessages[response.status] || 'Não foi possível concluir a operação.', body)
}

async function request<T>(path: string, user: SessionUser | null, init: RequestInit = {}): Promise<T> {
  const hasBody = init.body !== undefined
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: headersFor(user, hasBody),
  })
  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function loginVisitante(): Promise<SessionUser> {
  const result = await request<AuthResponse>(endpoints.visitante, null, { method: 'POST' })
  const accessToken = result.access_token ?? result.usuario.accessToken
  return {
    ...result.usuario,
    ...(accessToken ? { accessToken } : {}),
    expiresAt: Date.now() + (result.expires_in ?? 7200) * 1000,
  }
}

export async function loginGoogle(credential: string): Promise<SessionUser> {
  const result = await request<AuthResponse>(endpoints.google, null, {
    method: 'POST',
    body: JSON.stringify({ credential }),
  })
  const accessToken = result.access_token ?? result.usuario.accessToken
  return { ...result.usuario, ...(accessToken ? { accessToken } : {}) }
}

export async function planejarRoteiro(payload: PlanejamentoInput, user: SessionUser, signal?: AbortSignal): Promise<Roteiro> {
  return (await planejarRoteiroComTelemetria(payload, user, signal)).data
}

export async function planejarRoteiroComTelemetria(payload: PlanejamentoInput, user: SessionUser, signal?: AbortSignal): Promise<ApiResult<Roteiro>> {
  const startedAt = performance.now()
  const body = {
    origem_cidade: payload.origem.cidade, origem_uf: payload.origem.uf,
    destino_cidade: payload.destino.cidade, destino_uf: payload.destino.uf,
    dias_estadia: payload.dias, estilo_viagem: payload.estilo_viagem,
    preferencia_rota: payload.preferencia_rota, tipo_veiculo: payload.veiculo.tipo,
    consumo_medio: payload.veiculo.consumo, autonomia_km: payload.veiculo.autonomia_km,
    capacidade_veiculo: payload.veiculo.capacidade, preco_unidade: payload.veiculo.preco_unidade,
    passageiros: payload.passageiros,
  }
  const response = await fetch(`${API_BASE_URL}${endpoints.planejar}`, {
    method: 'POST', credentials: 'include', headers: headersFor(user, true), body: JSON.stringify(body), ...(signal ? { signal } : {}),
  })
  if (!response.ok) throw await parseError(response)
  const processHeader = response.headers.get('X-Process-Time')
  const requestId = response.headers.get('X-Request-ID') ?? undefined
  const telemetry = {
    totalTimeMs: performance.now() - startedAt,
    ...(processHeader ? { processTimeMs: Number(processHeader) * (Number(processHeader) < 10 ? 1000 : 1) } : {}),
    ...(requestId ? { requestId } : {}),
  }
  return { data: await response.json() as Roteiro, telemetry }
}

export function listarRoteiros(user: SessionUser, signal?: AbortSignal): Promise<Roteiro[]> {
  return request<Roteiro[]>(endpoints.historico, user, signal ? { signal } : {})
}

export function excluirRoteiro(id: string, user: SessionUser): Promise<void> {
  return request<void>(endpoints.roteiro(id), user, { method: 'DELETE' })
}

export function marcarParadaVisitada(roteiroId: string, paradaId: string, visitado: boolean, user: SessionUser): Promise<Roteiro> {
  return request<Roteiro>(endpoints.visita(roteiroId), user, {
    method: 'PATCH',
    body: JSON.stringify({ atrativo_id: paradaId, visitado }),
  })
}

export async function baixarGpx(id: string, user: SessionUser): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${endpoints.gpx}`, {
    method: 'POST',
    credentials: 'include',
    headers: headersFor(user, true),
    body: JSON.stringify({ roteiro_id: id }),
  })
  if (!response.ok) throw await parseError(response)
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `roteiro-${id}.gpx`
  anchor.click()
  URL.revokeObjectURL(url)
}

export async function* parseSseStream(stream: ReadableStream<Uint8Array>): AsyncGenerator<StreamGuiaEvent> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n')
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''

      for (const block of blocks) {
        const data = block.split('\n')
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trimStart())
          .join('\n')
        if (!data) continue
        const event = JSON.parse(data) as StreamGuiaEvent
        yield event
        if (event.done) return
      }

      if (done) break
    }

    if (buffer.trim()) {
      const data = buffer.split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trimStart())
        .join('\n')
      if (data) yield JSON.parse(data) as StreamGuiaEvent
    }
  } finally {
    reader.releaseLock()
  }
}

export async function* transmitirGuia(roteiro: Roteiro, parametros: PlanejamentoInput, user: SessionUser, signal?: AbortSignal): AsyncGenerator<StreamGuiaEvent> {
  const response = await fetch(`${API_BASE_URL}${endpoints.stream}`, {
    method: 'POST',
    credentials: 'include',
    headers: headersFor(user, true),
    body: JSON.stringify({
      destino: `${roteiro.destino.cidade} - ${roteiro.destino.uf}`,
      dias_estadia: parametros.dias,
      estilo_viagem: parametros.estilo_viagem,
      clima_info: roteiro.clima ?? {},
      atrativos: roteiro.atrativos ?? [],
      gastronomia: [],
    }),
    ...(signal ? { signal } : {}),
  })
  if (!response.ok) throw await parseError(response)
  if (!response.body) throw new ApiError(503, 'O navegador não recebeu o fluxo do guia.')
  yield* parseSseStream(response.body)
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return friendlyMessages[error.status] ?? error.message
  if (error instanceof DOMException && error.name === 'AbortError') return 'Operação cancelada.'
  return error instanceof Error ? error.message : 'Ocorreu um erro inesperado.'
}
