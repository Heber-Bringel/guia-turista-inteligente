import type { ProviderDiagnostic } from './api'

export const UFS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
  'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
] as const

export type Uf = (typeof UFS)[number]
export type EstiloViagem = 'economico' | 'cultural' | 'gastronomico' | 'aventura' | 'familia' | 'romantico'
export type PreferenciaRota = 'rapida' | 'economica' | 'cenica'
export type TipoVeiculo = 'gasolina' | 'etanol' | 'diesel' | 'eletrico' | 'hibrido'
export type RitmoViagem = 'tranquilo' | 'moderado' | 'intenso'
export type CanalDespacho = 'email' | 'whatsapp'

export interface LocalidadeInput {
  cidade: string
  uf: Uf | ''
}

export interface PlanejamentoInput {
  origem: LocalidadeInput
  destino: LocalidadeInput
  estilo_viagem: EstiloViagem
  dias: number
  preferencia_rota: PreferenciaRota
  veiculo: {
    tipo: TipoVeiculo
    consumo: number
    autonomia_km: number
    capacidade: number
    preco_unidade: number
  }
  passageiros: number
}

export interface Coordenada {
  latitude: number
  longitude: number
}

export interface Localidade extends Coordenada {
  cidade: string
  uf: string
}

export interface GeoJsonLineString {
  type: 'LineString'
  coordinates: Array<[number, number]>
}

export interface RotaAlternativa extends GeoJsonLineString {
  nome?: string
  distancia_km?: number
  duracao_minutos?: number
}

export interface Parada extends Coordenada {
  id?: string
  nome: string
  distancia_origem_km?: number
  estimada?: boolean
  visitado?: boolean
  cnpj?: string
  razao_social?: string
  avaliacao?: number
  tempo_autorizacao_anp?: string | number
  combustiveis?: string[]
  ranking_score?: number
  rodovia?: string
  municipio?: string
  uf?: string
  bandeira?: string
  endereco?: string
}

export interface Atrativo {
  id: string
  nome: string
  categoria?: string
  descricao?: string
  visitado: boolean
}

export interface Clima {
  temperatura_c?: number
  umidade_percentual?: number
  vento_kmh?: number
  descricao?: string
}

export interface Altimetria {
  ganho_m?: number
  perda_m?: number
  altitude_maxima_m?: number
  impacto_consumo_percentual?: number
}

export interface Custos {
  combustivel_ou_energia?: number
  pedagios?: number
  total?: number
  por_passageiro?: number
  moeda?: 'BRL'
  emissoes_kg_co2?: number
}

export interface Roteiro {
  id: string
  criado_em: string
  idioma?: string
  origem: Localidade
  destino: Localidade
  distancia_km: number
  duracao_minutos: number
  geometria: GeoJsonLineString
  alternativas?: RotaAlternativa[]
  paradas: Parada[]
  atrativos?: Atrativo[]
  clima?: Clima
  altimetria?: Altimetria
  custos?: Custos
  diagnosticos?: ProviderDiagnostic[]
  guia?: string
}

export interface MensagemChatItem {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatMensagem extends MensagemChatItem {
  id: string
  criado_em: string
  patrimonios_preservados?: string[]
  sugestoes_proximos_passos?: string[]
}

export interface ChatRoteiroRequest {
  destino: string
  dias_estadia?: number
  estilo_viagem?: EstiloViagem
  ritmo_viagem: RitmoViagem
  acompanhantes: string
  preferencias_gastronomia: string
  mensagem: string
  historico: MensagemChatItem[]
  clima_info?: Clima
  roteiro_id?: string
}

export interface ChatRoteiroResponse {
  resposta: string
  idioma: string
  destino: string
  roteiro_personalizado?: string
  patrimonios_preservados?: string[]
  sugestoes_proximos_passos?: string[]
  fallback_utilizado?: boolean
}

export interface DespacharRoteiroRequest {
  roteiro_id?: string
  canal: CanalDespacho
  destinatario: string
  nome_viajante?: string
  resumo_guia?: string
  roteiro?: Roteiro
}

export interface DespacharRoteiroResponse {
  status: string
  protocolo?: string
  canal: CanalDespacho
  destinatario?: string
  idioma?: string
  mensagem: string
}

export interface PlanningProgress {
  etapa: 'enviando' | 'calculando' | 'finalizando'
  mensagem: string
}
