"""Esquemas Pydantic v2 estritos para planejamento, geolocalização, postos ANP, chat IA, despacho multicanal e suporte."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

UFS_VALIDAS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

ProviderName = Literal["geocoding", "clima", "rota", "altimetria", "postos", "gemini"]
ProviderStatus = Literal["disponivel", "parcial", "indisponivel"]
EstiloViagem = Literal["cultural", "gastronomico", "ecoturismo", "familia", "romantico", "economico", "aventura"]
PreferenciaRota = Literal["rapida", "economica", "cenica"]
TipoVeiculo = Literal["gasolina", "etanol", "diesel", "eletrico", "hibrido", "combustivel"]
CanalDespacho = Literal["email", "whatsapp"]
RitmoViagem = Literal["tranquilo", "moderado", "intenso"]


def validar_cidade(v: str) -> str:
    """Valida e sanitiza o nome da cidade: remove espaços, não pode ser vazia e limite de 100 caracteres."""
    if not isinstance(v, str):
        raise ValueError("Cidade deve ser uma sequência de texto.")  # noqa: TRY004
    limpa = v.strip()
    if not limpa:
        raise ValueError("Cidade não pode ser vazia ou conter apenas espaços.")
    if len(limpa) > 100:
        raise ValueError("Nome da cidade não pode exceder 100 caracteres.")
    return limpa


def validar_uf(v: str) -> str:
    """Valida e padroniza a UF: deve ser uma das 27 siglas oficiais brasileiras em maiúsculas."""
    if not isinstance(v, str):
        raise ValueError("UF deve ser uma sequência de texto.")  # noqa: TRY004
    uf = v.strip().upper()
    if uf not in UFS_VALIDAS:
        raise ValueError(
            f"UF '{v}' inválida. Deve ser uma das 27 siglas oficiais brasileiras (ex: CE, PI, SP)."
        )
    return uf


class ProviderDiagnostic(BaseModel):
    """Diagnóstico individual do status de cada serviço externo integrado."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "provedor": "clima",
                "status": "disponivel",
                "mensagem": "Serviço meteorológico operacional",
            }
        },
    )

    provedor: ProviderName
    status: ProviderStatus
    mensagem: str | None = None


class Localidade(BaseModel):
    """Coordenadas e identificação de uma localidade geográfica."""

    model_config = ConfigDict(extra="forbid")

    cidade: str
    uf: str
    latitude: float
    longitude: float


class GeoJsonGeometry(BaseModel):
    """Estrutura GeoJSON LineString para representação de polilinhas de rota."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]]


class RotaAlternativa(GeoJsonGeometry):
    """Rota alternativa: a geometria GeoJSON (compatível com o mapa) mais nome e métricas da sugestão."""

    nome: str | None = None
    distancia_km: float | None = None
    duracao_minutos: float | None = None


class ParadaItem(BaseModel):
    """Ponto de parada programada ao longo da rota com dados regulatórios da ANP (V3)."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    nome: str
    latitude: float
    longitude: float
    distancia_origem_km: float | None = None
    estimada: bool = True
    visitado: bool = False
    # Atributos regulatórios ANP (V3)
    cnpj: str | None = None
    razao_social: str | None = None
    avaliacao: float | None = None
    tempo_autorizacao_anp: str | int | None = None
    combustiveis: list[str] = Field(default_factory=list)
    ranking_score: float | None = None
    rodovia: str | None = None
    municipio: str | None = None
    uf: str | None = None


class AtrativoItem(BaseModel):
    """Ponto turístico ou cultural sugerido no destino."""

    model_config = ConfigDict(extra="forbid")

    id: str
    nome: str
    categoria: str | None = None
    descricao: str | None = None
    visitado: bool = False


class ClimaInfo(BaseModel):
    """Informações meteorológicas do destino."""

    model_config = ConfigDict(extra="forbid")

    temperatura_c: float | None = None
    umidade_percentual: float | None = None
    vento_kmh: float | None = None
    descricao: str | None = None


class PerfilAltimetricoPonto(BaseModel):
    """Amostra do perfil de elevação ao longo da rota."""

    model_config = ConfigDict(extra="forbid")

    distancia_km: float
    altitude_m: float
    latitude: float | None = None
    longitude: float | None = None


class AltimetriaInfo(BaseModel):
    """Dados de altimetria e perfil de elevação do percurso."""

    model_config = ConfigDict(extra="forbid")

    ganho_m: float | None = None
    perda_m: float | None = None
    altitude_maxima_m: float | None = None
    altitude_minima_m: float | None = None
    desnivel_liquido_m: float | None = None
    impacto_consumo_percentual: float | None = None
    fonte: str | None = None
    perfil: list[PerfilAltimetricoPonto] | None = None


class CustosInfo(BaseModel):
    """Estimativa financeira do trajeto."""

    model_config = ConfigDict(extra="forbid")

    combustivel_ou_energia: float | None = None
    pedagios: float | None = None
    total: float | None = None
    por_passageiro: float | None = None
    moeda: Literal["BRL"] = "BRL"
    emissoes_kg_co2: float | None = None


class RoteiroRequest(BaseModel):
    """Requisição principal de planejamento de roteiro."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "origem_cidade": "Teresina",
                "origem_uf": "PI",
                "destino_cidade": "Parnaíba",
                "destino_uf": "PI",
                "dias_estadia": 3,
                "estilo_viagem": "cultural",
                "preferencia_rota": "rapida",
                "tipo_veiculo": "gasolina",
                "consumo_medio": 12.0,
                "autonomia_km": 500.0,
                "capacidade_veiculo": 50.0,
                "preco_unidade": 5.89,
                "passageiros": 2,
            }
        },
    )

    origem_cidade: str = Field(..., description="Cidade de partida.")
    origem_uf: str = Field(..., min_length=2, max_length=2, description="UF de partida (sigla de 2 letras).")
    destino_cidade: str = Field(..., description="Cidade de destino.")
    destino_uf: str = Field(..., min_length=2, max_length=2, description="UF de destino (sigla de 2 letras).")
    dias_estadia: Annotated[int, Field(ge=1, le=5, description="Dias no destino (entre 1 e 5).")]
    estilo_viagem: EstiloViagem = Field(
        default="cultural",
        description="Estilo da viagem: cultural, gastronomico, ecoturismo, familia, romantico, economico ou aventura.",
    )
    preferencia_rota: PreferenciaRota = Field(
        default="rapida",
        description="Critério de roteamento: rapida, economica ou cenica.",
    )
    tipo_veiculo: TipoVeiculo = Field(
        default="gasolina",
        description="Tipo de motorização/veículo.",
    )
    consumo_medio: Annotated[float, Field(gt=0, le=100.0, description="Consumo médio (km/L ou km/kWh).")] = 12.0
    autonomia_km: Annotated[float, Field(gt=0, le=3000.0, description="Autonomia máxima em km.")] = 500.0
    capacidade_veiculo: Annotated[float, Field(gt=0, le=500.0, description="Capacidade do tanque (L) ou bateria (kWh).")] = 50.0
    preco_unidade: Annotated[float, Field(gt=0, le=50.0, description="Preço por litro ou por kWh em R$.")] = 5.89
    passageiros: Annotated[int, Field(ge=1, le=8, description="Número de ocupantes no veículo.")] = 1

    @field_validator("origem_cidade", "destino_cidade")
    @classmethod
    def validar_cidades(cls, v: str) -> str:
        return validar_cidade(v)

    @field_validator("origem_uf", "destino_uf")
    @classmethod
    def validar_ufs(cls, v: str) -> str:
        return validar_uf(v)


class MapaRotaRequest(BaseModel):
    """Requisição leve para traçado visual da rota no mapa."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "origem_cidade": "Fortaleza",
                "origem_uf": "CE",
                "destino_cidade": "Natal",
                "destino_uf": "RN",
                "preferencia_rota": "rapida",
            }
        },
    )

    origem_cidade: str
    origem_uf: str
    destino_cidade: str
    destino_uf: str
    preferencia_rota: PreferenciaRota = "rapida"

    @field_validator("origem_cidade", "destino_cidade")
    @classmethod
    def validar_cidades(cls, v: str) -> str:
        return validar_cidade(v)

    @field_validator("origem_uf", "destino_uf")
    @classmethod
    def validar_ufs(cls, v: str) -> str:
        return validar_uf(v)


class CustosRequest(BaseModel):
    """Requisição para cálculo detalhado de custos e emissões."""

    model_config = ConfigDict(extra="forbid")

    distancia_km: Annotated[float, Field(ge=0)]
    tipo_veiculo: TipoVeiculo = "gasolina"
    consumo_medio: Annotated[float, Field(gt=0)] = 12.0
    preco_unidade: Annotated[float, Field(gt=0)] = 5.89
    capacidade_veiculo: Annotated[float, Field(gt=0)] = 50.0
    passageiros: Annotated[int, Field(ge=1, le=8)] = 1
    pedagios_estimados: Annotated[float, Field(ge=0)] = 0.0


class GuiaStreamRequest(BaseModel):
    """Payload para solicitação de streaming progressivo do guia turístico."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "destino": "Brasília - DF",
                "dias_estadia": 3,
                "estilo_viagem": "cultural",
                "clima_info": {"temperatura_c": 28.5, "descricao": "Céu limpo"},
                "atrativos": [{"id": "atr_1", "nome": "Catedral Metropolitana", "visitado": False}],
                "gastronomia": ["Galinhada com pequi"],
            }
        },
    )

    destino: str = Field(..., min_length=3, description="Destino formatado Cidade - UF.")
    dias_estadia: Annotated[int, Field(ge=1, le=5)] = 1
    estilo_viagem: EstiloViagem = "cultural"
    clima_info: dict[str, Any] = Field(default_factory=dict)
    atrativos: list[dict[str, Any]] = Field(default_factory=list)
    gastronomia: list[str] = Field(default_factory=list)


class MensagemChatItem(BaseModel):
    """Mensagem individual do diálogo multi-turno com o Gemini."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"] = "user"
    content: str = Field(..., min_length=1, max_length=2000)


class ChatRoteiroRequest(BaseModel):
    """Payload para diálogo interativo e personalização de roteiro com Gemini (V3)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "destino": "Piripiri - PI",
                "dias_estadia": 2,
                "estilo_viagem": "ecoturismo",
                "ritmo_viagem": "tranquilo",
                "acompanhantes": "família com crianças",
                "preferencias_gastronomia": "comida típica piauiense e doces caseiros",
                "mensagem": "Quero incluir o Parque Nacional de Sete Cidades e o Açude Caldeirão no roteiro.",
                "historico": [],
            }
        },
    )

    destino: str = Field(..., min_length=2, max_length=120, description="Cidade ou destino da viagem.")
    dias_estadia: Annotated[int, Field(ge=1, le=10)] = 2
    estilo_viagem: EstiloViagem = "cultural"
    ritmo_viagem: str = Field(default="moderado", max_length=80, description="Ritmo: tranquilo, moderado ou intenso.")
    acompanhantes: str = Field(default="casal", max_length=120, description="Perfil dos acompanhantes.")
    preferencias_gastronomia: str = Field(
        default="culinária típica regional",
        max_length=200,
        description="Preferências gastronômicas do viajante.",
    )
    mensagem: str = Field(..., min_length=1, max_length=1500, description="Mensagem atual enviada pelo viajante.")
    historico: list[MensagemChatItem] = Field(default_factory=list, description="Histórico de turnos anteriores.")
    clima_info: dict[str, Any] = Field(default_factory=dict)
    roteiro_id: str | None = None


class ChatRoteiroResponse(BaseModel):
    """Resposta do diálogo interativo com Gemini, adaptada ao idioma de Accept-Language."""

    model_config = ConfigDict(extra="forbid")

    resposta: str
    idioma: str = "pt"
    destino: str
    roteiro_personalizado: str | None = None
    patrimonios_preservados: list[str] = Field(default_factory=list)
    sugestoes_proximos_passos: list[str] = Field(default_factory=list)
    fallback_utilizado: bool = False


class DespacharRoteiroRequest(BaseModel):
    """Requisição de entrega multicanal exclusiva do roteiro por E-mail ou WhatsApp via n8n (V3)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "roteiro_id": "rot_7f8a9b1c",
                "canal": "email",
                "destinatario": "viajante@exemplo.com",
                "nome_viajante": "Mikaelle Barroso",
                "resumo_guia": "Roteiro personalizado para Sete Cidades e Delta do Parnaíba.",
            }
        },
    )

    roteiro_id: str | None = Field(default=None, description="ID do roteiro salvo no histórico do usuário.")
    canal: CanalDespacho = Field(..., description="Canal de entrega: 'email' ou 'whatsapp'.")
    destinatario: str = Field(..., min_length=5, max_length=180, description="E-mail ou telefone WhatsApp com DDI/DDD.")
    nome_viajante: str | None = Field(default="Viajante", max_length=100)
    resumo_guia: str | None = Field(default=None, max_length=8000)
    roteiro: dict[str, Any] | None = Field(
        default=None,
        description="Dados do roteiro caso enviado diretamente pelo estado da SPA.",
    )

    @field_validator("destinatario")
    @classmethod
    def validar_destinatario(cls, v: str) -> str:
        limpo = v.strip()
        if not limpo:
            raise ValueError("O destinatário não pode ser vazio.")
        return limpo


class DespacharRoteiroResponse(BaseModel):
    """Confirmação de agendamento do despacho multicanal em BackgroundTasks."""

    model_config = ConfigDict(extra="forbid")

    status: str = "agendado"
    protocolo: str
    canal: CanalDespacho
    destinatario: str
    idioma: str = "pt"
    mensagem: str


class MarcarVisitaRequest(BaseModel):
    """Requisição para alternar status de visita de um atrativo ou parada."""

    model_config = ConfigDict(extra="forbid")

    atrativo_id: str = Field(..., min_length=1)
    visitado: bool = Field(...)


class ExportarGpxRequest(BaseModel):
    """Requisição para exportação de arquivo GPX 1.1 da rota."""

    model_config = ConfigDict(extra="forbid")

    roteiro_id: str = Field(..., min_length=1)


class CompartilharRoteiroRequest(BaseModel):
    """Requisição de envio assíncrono do roteiro por e-mail ou link público."""

    model_config = ConfigDict(extra="forbid")

    roteiro_id: str = Field(..., min_length=1)
    email_destinatario: str = Field(..., min_length=5)


class RoteiroResponse(BaseModel):
    """Resposta completa do planejamento do roteiro turístico."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "rot_7f8a9b1c",
                "criado_em": "2026-11-27T10:30:00Z",
                "idioma": "pt",
                "origem": {
                    "cidade": "Teresina",
                    "uf": "PI",
                    "latitude": -5.089,
                    "longitude": -42.801,
                },
                "destino": {
                    "cidade": "Parnaíba",
                    "uf": "PI",
                    "latitude": -2.905,
                    "longitude": -41.776,
                },
                "distancia_km": 338.0,
                "duracao_minutos": 285.0,
                "geometria": {
                    "type": "LineString",
                    "coordinates": [[-42.801, -5.089], [-41.778, -4.273], [-41.776, -2.905]],
                },
                "alternativas": [],
                "paradas": [
                    {
                        "id": "posto_anp_1",
                        "nome": "Posto Piripiri BR-343 (km 160)",
                        "latitude": -4.273,
                        "longitude": -41.778,
                        "distancia_origem_km": 160.0,
                        "estimada": False,
                        "visitado": False,
                        "cnpj": "07.456.789/0001-90",
                        "razao_social": "Auto Posto Caldeirão da BR-343 Ltda",
                        "avaliacao": 4.8,
                        "tempo_autorizacao_anp": "14 anos",
                        "combustiveis": ["Gasolina Comum", "Gasolina Aditivada", "Etanol", "Diesel S10"],
                        "ranking_score": 9.4,
                        "rodovia": "BR-343",
                        "municipio": "Piripiri",
                        "uf": "PI",
                    }
                ],
                "atrativos": [
                    {
                        "id": "atr_1",
                        "nome": "Parque Nacional de Sete Cidades",
                        "categoria": "Patrimônio Natural e Arqueológico",
                        "descricao": "Formações rochosas milenares e inscrições rupestres.",
                        "visitado": False,
                    }
                ],
                "clima": {
                    "temperatura_c": 31.0,
                    "umidade_percentual": 55.0,
                    "vento_kmh": 14.0,
                    "descricao": "Ensolarado",
                },
                "altimetria": {
                    "ganho_m": 240.0,
                    "perda_m": 310.0,
                    "altitude_maxima_m": 180.0,
                    "impacto_consumo_percentual": 2.0,
                },
                "custos": {
                    "combustivel_ou_energia": 169.20,
                    "pedagios": 0.0,
                    "total": 169.20,
                    "por_passageiro": 84.60,
                    "moeda": "BRL",
                    "emissoes_kg_co2": 64.8,
                },
                "diagnosticos": [
                    {"provedor": "geocoding", "status": "disponivel", "mensagem": "Serviço operacional"},
                    {"provedor": "clima", "status": "disponivel", "mensagem": "Serviço operacional"},
                    {"provedor": "rota", "status": "disponivel", "mensagem": "Serviço operacional"},
                    {"provedor": "altimetria", "status": "disponivel", "mensagem": "Serviço operacional"},
                    {"provedor": "postos", "status": "disponivel", "mensagem": "Postos regulados ANP localizados"},
                    {"provedor": "gemini", "status": "disponivel", "mensagem": "Guia personalizado disponível"},
                ],
                "guia": "Guia formatado com atrações culturais e gastronomia...",
            }
        },
    )

    id: str
    criado_em: str
    idioma: str = "pt"
    origem: Localidade
    destino: Localidade
    distancia_km: float
    duracao_minutos: float
    geometria: GeoJsonGeometry
    alternativas: list[RotaAlternativa] | None = None
    paradas: list[ParadaItem] = Field(default_factory=list)
    atrativos: list[AtrativoItem] = Field(default_factory=list)
    clima: ClimaInfo | None = None
    altimetria: AltimetriaInfo | None = None
    custos: CustosInfo | None = None
    diagnosticos: list[ProviderDiagnostic] = Field(default_factory=list)
    guia: str | None = None
