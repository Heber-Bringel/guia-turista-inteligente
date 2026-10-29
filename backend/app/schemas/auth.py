"""Esquemas Pydantic v2 estritos para autenticação e perfis de usuário."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class TokenGoogleRequest(BaseModel):
    """Payload recebido para autenticação via Google OAuth."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "credential": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1NiJ9.exemplo_token_google..."
            }
        },
    )

    credential: str = Field(
        ...,
        min_length=10,
        description="JWT do Google Identity Services emitido no frontend.",
    )


class UsuarioPerfil(BaseModel):
    """Representação padronizada do usuário na sessão ativa."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "usr_google_1029384756",
                "nome": "Mikaelle Barroso",
                "email": "mikaelle@example.com",
                "foto": "https://lh3.googleusercontent.com/a/default-user",
                "modo": "google",
                "accessToken": "usr_google_1029384756",
                "expiresAt": 1793280000000,
            }
        },
    )

    id: str = Field(..., description="Identificador único (ID Google ou visitante_uuid).")
    nome: str = Field(..., description="Nome do usuário ou 'Viajante Visitante'.")
    email: str | None = Field(default=None, description="E-mail do usuário (opcional em visitantes).")
    foto: str | None = Field(default=None, description="URL da foto de perfil.")
    modo: Literal["google", "visitante"] = Field(
        ..., description="Modo de acesso: 'google' ou 'visitante'."
    )
    accessToken: str | None = Field(
        default=None, description="Token de acesso ou identificador de sessão para a API."
    )
    expiresAt: int | None = Field(
        default=None, description="Timestamp Unix em milissegundos para expiração da sessão."
    )


class LoginResponse(BaseModel):
    """Resposta estruturada enviada ao frontend após login com sucesso."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "usuario": {
                    "id": "visitante_7f8a9b1c2d3e",
                    "nome": "Viajante Visitante",
                    "email": None,
                    "foto": "/static/img/visitante.svg",
                    "modo": "visitante",
                    "accessToken": "visitante_7f8a9b1c2d3e",
                    "expiresAt": 1793280000000,
                },
                "access_token": "visitante_7f8a9b1c2d3e",
                "expires_in": 7200,
            }
        },
    )

    usuario: UsuarioPerfil
    access_token: str | None = Field(default=None, description="Token bearer de sessão.")
    expires_in: int | None = Field(default=7200, description="Duração em segundos da sessão.")

