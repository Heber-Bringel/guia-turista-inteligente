"""Esquemas Pydantic v2 estritos para planejamento, geolocalização, telemetria e roteiros."""

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


def validar_cidade(v: str) -> str:
    """Valida e sanitiza o nome da cidade: remove espaços, não pode ser vazia e limite de 100 caracteres."""
    if not isinstance(v, str):
        raise ValueError("Cidade deve ser uma sequência de texto.")
    limpa = v.strip()
    if not limpa:
        raise ValueError("Cidade não pode ser vazia ou conter apenas espaços.")
    if len(limpa) > 100:
        raise ValueError("Nome da cidade não pode exceder 100 caracteres.")
    return limpa


def validar_uf(v: str) -> str:
    """Valida e padroniza a UF: deve ser uma das 27 siglas oficiais brasileiras em maiúsculas."""
    if not isinstance(v, str):
        raise ValueError("UF deve ser uma sequência de texto.")
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
                "mensagem": "Open-Meteo respondeu em 120ms",
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
    """Ponto de parada programada ao longo da rota."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    nome: str
    latitude: float
    longitude: float
    distancia_origem_km: float | None = None
    estimada: bool = True
    visitado: bool = False


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
                "destino_cidade": "Brasília",
                "destino_uf": "DF",
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
                "criado_em": "2026-10-29T10:30:00Z",
                "origem": {
                    "cidade": "Teresina",
                    "uf": "PI",
                    "latitude": -5.089,
                    "longitude": -42.801,
                },
                "destino": {
                    "cidade": "Brasília",
                    "uf": "DF",
                    "latitude": -15.779,
                    "longitude": -47.929,
                },
                "distancia_km": 1674.6,
                "duracao_minutos": 1298.0,
                "geometria": {
                    "type": "LineString",
                    "coordinates": [[-42.801, -5.089], [-47.929, -15.779]],
                },
                "alternativas": [],
                "paradas": [
                    {
                        "id": "parada_1",
                        "nome": "Parada Estratégica km 510",
                        "latitude": -9.123,
                        "longitude": -45.456,
                        "distancia_origem_km": 510.0,
                        "estimada": True,
                        "visitado": False,
                    }
                ],
                "atrativos": [
                    {
                        "id": "atr_1",
                        "nome": "Congresso Nacional",
                        "categoria": "Histórico/Político",
                        "descricao": "Arquitetura icônica de Oscar Niemeyer.",
                        "visitado": False,
                    }
                ],
                "clima": {
                    "temperatura_c": 28.5,
                    "umidade_percentual": 35.0,
                    "vento_kmh": 12.0,
                    "descricao": "Ensolarado",
                },
                "altimetria": {
                    "ganho_m": 850.0,
                    "perda_m": 220.0,
                    "altitude_maxima_m": 1172.0,
                    "impacto_consumo_percentual": 4.5,
                },
                "custos": {
                    "combustivel_ou_energia": 821.50,
                    "pedagios": 0.0,
                    "total": 821.50,
                    "por_passageiro": 410.75,
                    "moeda": "BRL",
                    "emissoes_kg_co2": 312.4,
                },
                "diagnosticos": [
                    {"provedor": "geocoding", "status": "disponivel", "mensagem": "OK"},
                    {"provedor": "clima", "status": "disponivel", "mensagem": "OK"},
                    {"provedor": "rota", "status": "disponivel", "mensagem": "OK"},
                    {"provedor": "altimetria", "status": "disponivel", "mensagem": "OK"},
                    {"provedor": "postos", "status": "disponivel", "mensagem": "OK"},
                    {"provedor": "gemini", "status": "disponivel", "mensagem": "OK"},
                ],
                "guia": "Guia formatado com atrações culturais e gastronomia...",
            }
        },
    )

    id: str
    criado_em: str
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

