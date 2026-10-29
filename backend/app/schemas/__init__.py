"""Pacote de esquemas de validação Pydantic."""

from app.schemas.auth import LoginResponse, TokenGoogleRequest, UsuarioPerfil
from app.schemas.roteiros import (
    AltimetriaInfo,
    AtrativoItem,
    ClimaInfo,
    CompartilharRoteiroRequest,
    CustosInfo,
    CustosRequest,
    ExportarGpxRequest,
    GeoJsonGeometry,
    GuiaStreamRequest,
    Localidade,
    MapaRotaRequest,
    MarcarVisitaRequest,
    ParadaItem,
    ProviderDiagnostic,
    RoteiroRequest,
    RoteiroResponse,
)

__all__ = [
    "AltimetriaInfo",
    "AtrativoItem",
    "ClimaInfo",
    "CompartilharRoteiroRequest",
    "CustosInfo",
    "CustosRequest",
    "ExportarGpxRequest",
    "GeoJsonGeometry",
    "GuiaStreamRequest",
    "Localidade",
    "LoginResponse",
    "MapaRotaRequest",
    "MarcarVisitaRequest",
    "ParadaItem",
    "ProviderDiagnostic",
    "RoteiroRequest",
    "RoteiroResponse",
    "TokenGoogleRequest",
    "UsuarioPerfil",
]

