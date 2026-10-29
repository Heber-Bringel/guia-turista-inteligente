export type ProviderName = 'geocoding' | 'clima' | 'rota' | 'altimetria' | 'postos' | 'gemini'

export type ProviderStatus = 'disponivel' | 'parcial' | 'indisponivel'

export interface ProviderDiagnostic {
  provedor: ProviderName
  status: ProviderStatus
  mensagem?: string
}

export interface ApiErrorBody {
  detail?: string | Array<{ loc?: Array<string | number>; msg: string }>
  message?: string
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly details?: ApiErrorBody,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export interface StreamGuiaEvent {
  chunk: string
  done: boolean
  fallback?: boolean
}

export interface SessionUser {
  id: string
  nome: string
  email?: string
  foto?: string
  modo: 'google' | 'visitante'
  accessToken?: string
  expiresAt?: number
}

export interface AuthResponse {
  usuario: SessionUser
  access_token?: string
  expires_in?: number
}

export interface RequestTelemetry {
  processTimeMs?: number
  totalTimeMs: number
  requestId?: string
}

export interface ApiResult<T> {
  data: T
  telemetry: RequestTelemetry
}
