import { getCurrentLanguage, getTranslations } from '../i18n/language'
import {
  ApiError,
  type ApiErrorBody,
  type AuthResponse,
  type SessionUser,
  type StreamGuiaEvent,
  type SupportedLanguage,
} from '../types/api'
import type {
  ChatRoteiroRequest,
  ChatRoteiroResponse,
  DespacharRoteiroRequest,
  DespacharRoteiroResponse,
  PlanejamentoInput,
  Roteiro,
} from '../types/roteiro'

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
  chat: '/roteiros/chat',
  despachar: '/roteiros/despachar',
} as const

function friendlyStatusMessage(status: number, language?: SupportedLanguage): string {
  const t = getTranslations(language)
  if (status === 401) return t.errorSessionExpired
  if (status === 409) return t.errorConflict
  if (status === 422 || status === 400) return t.errorValidation
  if (status >= 500) return t.errorServiceFriendly
  return t.errorGenericFriendly
}

function headersFor(user: SessionUser | null, hasBody: boolean, language?: SupportedLanguage): Headers {
  const activeLanguage = language ?? getCurrentLanguage()
  const headers = new Headers({
    Accept: 'application/json',
    'Accept-Language': activeLanguage,
  })
  if (hasBody) headers.set('Content-Type', 'application/json')
  if (user?.accessToken) headers.set('Authorization', `Bearer ${user.accessToken}`)
  if (user?.id) headers.set('X-User-Id', user.id)
  return headers
}

async function parseError(response: Response, language?: SupportedLanguage): Promise<ApiError> {
  let body: ApiErrorBody | undefined
  try {
    body = await response.json() as ApiErrorBody
  } catch {
    body = undefined
  }

  // Higienização V3: erros 5xx nunca expõem mensagens cruas ou stack traces para a interface pública.
  if (response.status >= 500) {
    return new ApiError(response.status, friendlyStatusMessage(response.status, language))
  }

  const detail = typeof body?.detail === 'string' ? body.detail : body?.message
  const safeMessage = response.status === 401 || response.status === 409 || response.status === 422
    ? friendlyStatusMessage(response.status, language)
    : detail || friendlyStatusMessage(response.status, language)

  return new ApiError(response.status, safeMessage, body)
}

async function request<T>(
  path: string,
  user: SessionUser | null,
  init: RequestInit = {},
  language?: SupportedLanguage,
): Promise<T> {
  const hasBody = init.body !== undefined
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: headersFor(user, hasBody, language),
  })
  if (!response.ok) throw await parseError(response, language)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function loginVisitante(language?: SupportedLanguage): Promise<SessionUser> {
  const result = await request<AuthResponse>(endpoints.visitante, null, { method: 'POST' }, language)
  const accessToken = result.access_token ?? result.usuario.accessToken
  return {
    ...result.usuario,
    ...(accessToken ? { accessToken } : {}),
    expiresAt: Date.now() + (result.expires_in ?? 7200) * 1000,
  }
}

export async function loginGoogle(credential: string, language?: SupportedLanguage): Promise<SessionUser> {
  const result = await request<AuthResponse>(
    endpoints.google,
    null,
    {
      method: 'POST',
      body: JSON.stringify({ credential }),
    },
    language,
  )
  const accessToken = result.access_token ?? result.usuario.accessToken
  return { ...result.usuario, ...(accessToken ? { accessToken } : {}) }
}

export async function planejarRoteiro(
  payload: PlanejamentoInput,
  user: SessionUser,
  signal?: AbortSignal,
  language?: SupportedLanguage,
): Promise<Roteiro> {
  const body = {
    origem_cidade: payload.origem.cidade,
    origem_uf: payload.origem.uf,
    destino_cidade: payload.destino.cidade,
    destino_uf: payload.destino.uf,
    dias_estadia: payload.dias,
    estilo_viagem: payload.estilo_viagem,
    preferencia_rota: payload.preferencia_rota,
    tipo_veiculo: payload.veiculo.tipo,
    consumo_medio: payload.veiculo.consumo,
    autonomia_km: payload.veiculo.autonomia_km,
    capacidade_veiculo: payload.veiculo.capacidade,
    preco_unidade: payload.veiculo.preco_unidade,
    passageiros: payload.passageiros,
  }
  return request<Roteiro>(
    endpoints.planejar,
    user,
    {
      method: 'POST',
      body: JSON.stringify(body),
      ...(signal ? { signal } : {}),
    },
    language,
  )
}

export function listarRoteiros(
  user: SessionUser,
  signal?: AbortSignal,
  language?: SupportedLanguage,
): Promise<Roteiro[]> {
  return request<Roteiro[]>(endpoints.historico, user, signal ? { signal } : {}, language)
}

export function excluirRoteiro(id: string, user: SessionUser, language?: SupportedLanguage): Promise<void> {
  return request<void>(endpoints.roteiro(id), user, { method: 'DELETE' }, language)
}

export function marcarParadaVisitada(
  roteiroId: string,
  paradaId: string,
  visitado: boolean,
  user: SessionUser,
  language?: SupportedLanguage,
): Promise<Roteiro> {
  return request<Roteiro>(
    endpoints.visita(roteiroId),
    user,
    {
      method: 'PATCH',
      body: JSON.stringify({ atrativo_id: paradaId, visitado }),
    },
    language,
  )
}

export function conversarRoteiro(
  payload: ChatRoteiroRequest,
  user: SessionUser,
  language?: SupportedLanguage,
  signal?: AbortSignal,
): Promise<ChatRoteiroResponse> {
  return request<ChatRoteiroResponse>(
    endpoints.chat,
    user,
    {
      method: 'POST',
      body: JSON.stringify(payload),
      ...(signal ? { signal } : {}),
    },
    language,
  )
}

export function despacharRoteiro(
  payload: DespacharRoteiroRequest,
  user: SessionUser,
  language?: SupportedLanguage,
): Promise<DespacharRoteiroResponse> {
  return request<DespacharRoteiroResponse>(
    endpoints.despachar,
    user,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    language,
  )
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
        const data = block
          .split('\n')
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
      const data = buffer
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trimStart())
        .join('\n')
      if (data) yield JSON.parse(data) as StreamGuiaEvent
    }
  } finally {
    reader.releaseLock()
  }
}

export async function* transmitirGuia(
  roteiro: Roteiro,
  parametros: PlanejamentoInput,
  user: SessionUser,
  signal?: AbortSignal,
  language?: SupportedLanguage,
): AsyncGenerator<StreamGuiaEvent> {
  const response = await fetch(`${API_BASE_URL}${endpoints.stream}`, {
    method: 'POST',
    credentials: 'include',
    headers: headersFor(user, true, language),
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
  if (!response.ok) throw await parseError(response, language)
  if (!response.body) throw new ApiError(503, friendlyStatusMessage(503, language))
  yield* parseSseStream(response.body)
}

export function errorMessage(error: unknown, language?: SupportedLanguage): string {
  const t = getTranslations(language)
  if (error instanceof ApiError) {
    if (error.status >= 500) return t.errorServiceFriendly
    return error.message || friendlyStatusMessage(error.status, language)
  }
  if (error instanceof DOMException && error.name === 'AbortError') return t.errorCancelled
  return t.errorGenericFriendly
}
