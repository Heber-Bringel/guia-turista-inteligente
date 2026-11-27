"""Configurações centrais da aplicação carregadas via Pydantic Settings e variáveis de ambiente."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais do microsserviço FastAPI (V3 EDA com n8n)."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Guia do Turista Inteligente"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = False

    PORT: int = Field(default=8001, description="Porta do servidor ASGI.")
    HOST: str = Field(default="0.0.0.0", description="Host de binding.")

    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
        description="Origens permitidas para requisições cross-origin (SPA React).",
    )

    GEMINI_API_KEY: str = Field(default="", description="Chave da API do Google Gemini.")
    GEMINI_MODEL: str = Field(default="", description="Modelo preferencial do Google Gemini.")
    GOOGLE_CLIENT_ID: str = Field(
        default="", description="Client ID do Google Identity Services para validar tokens no backend."
    )

    DATA_FILE_PATH: str = Field(
        default="static/data/viagens.json",
        description="Caminho relativo ou absoluto do arquivo JSON de persistência das viagens.",
    )

    # Segurança Operacional (ChatOps / Suporte Restrito)
    SUPPORT_API_KEY: str = Field(
        default="guia-turista-support-key-v3",
        description="Chave obrigatória no cabeçalho X-Support-Key para endpoints de suporte e ChatOps.",
    )

    # Orquestração n8n (Arquitetura Orientada a Eventos - EDA)
    N8N_BASE_URL: str = Field(
        default="http://localhost:5678",
        description="URL base do servidor n8n para disparo de webhooks.",
    )
    N8N_WEBHOOK_DLQ: str = Field(
        default="/webhook/turismo-dlq",
        description="Caminho do webhook da Dead Letter Queue (WF1 - Alerta Telegram).",
    )
    N8N_WEBHOOK_DESPACHAR_ROTEIRO: str = Field(
        default="/webhook/turismo-despachar-roteiro",
        description="Caminho do webhook de despacho multicanal E-mail/WhatsApp (WF3).",
    )
    N8N_WEBHOOK_CLIMA: str = Field(
        default="/webhook/turismo-clima",
        description="Caminho do webhook de avaliação climática com Gemini (WF4).",
    )
    TIMEOUT_N8N: float = Field(
        default=5.0,
        description="Timeout defensivo em segundos para webhooks disparados ao n8n em BackgroundTasks.",
    )

    TIMEOUT_SEGUNDOS: float = Field(
        default=10.0, description="Timeout global padrão para chamadas HTTP externas."
    )
    TIMEOUT_GEOCODING: float = Field(default=4.0, description="Timeout específico para Geocoding.")
    TIMEOUT_CLIMA: float = Field(default=4.0, description="Timeout específico para Open-Meteo.")
    TIMEOUT_ROTA: float = Field(default=6.0, description="Timeout específico para OSRM.")
    TIMEOUT_GEMINI: float = Field(default=8.0, description="Timeout específico para IA.")

    VISITANTE_TTL_SEGUNDOS: int = Field(
        default=7200, description="TTL em segundos (2h) para sessões voláteis de visitantes."
    )

    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(
        default=3, description="Número consecutivo de falhas para abrir o circuito."
    )
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: float = Field(
        default=30.0, description="Tempo em segundos que o circuito permanece aberto antes de testar recuperação."
    )

    def model_post_init(self, __context: object, /) -> None:
        """Propaga GEMINI_MODEL para os.environ se definido no .env e ausente no ambiente."""
        import os

        if self.GEMINI_MODEL and "GEMINI_MODEL" not in os.environ:
            os.environ["GEMINI_MODEL"] = self.GEMINI_MODEL

    def obter_url_webhook(self, caminho_ou_url: str) -> str:
        """Resolve a URL completa de um webhook do n8n."""
        alvo = caminho_ou_url.strip()
        if alvo.startswith(("http://", "https://")):
            return alvo
        base = self.N8N_BASE_URL.rstrip("/")
        sufixo = alvo if alvo.startswith("/") else f"/{alvo}"
        return f"{base}{sufixo}"

    def obter_caminho_dados(self) -> Path:
        """Resolve o caminho absoluto para o arquivo de persistência JSON."""
        caminho = Path(self.DATA_FILE_PATH)
        if not caminho.is_absolute():
            # Tenta resolver a partir da raiz do projeto ou diretório atual
            raiz_projeto = Path(__file__).resolve().parent.parent.parent.parent
            candidato_raiz = raiz_projeto / self.DATA_FILE_PATH
            if candidato_raiz.parent.exists():
                return candidato_raiz
            # Se não, resolve a partir do diretório do backend
            candidato_backend = Path(__file__).resolve().parent.parent.parent / self.DATA_FILE_PATH
            if candidato_backend.parent.exists():
                return candidato_backend
        return caminho


settings = Settings()
