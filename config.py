# Configurações e constantes do sistema

import json
import os
from pathlib import Path

# Porta padrão de execução do servidor Flask
PORT: int = 8001

# Caminhos de arquivos estáticos e bases de dados JSON
BASE_DIR: Path = Path(__file__).resolve().parent
ENV_FILE: Path = BASE_DIR / ".env"

# Carrega variáveis do .env caso ainda não estejam definidas no ambiente
if ENV_FILE.is_file():
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, _, valor = linha.partition("=")
                chave = chave.strip()
                valor = valor.strip()
                if chave and chave not in os.environ:
                    os.environ[chave] = valor

# Chaves e credenciais de integração externa
GEMINI_KEY: str = os.getenv("GEMINI_API_KEY", "")
GOOGLE_CLIENT_ID: str = os.getenv(
    "GOOGLE_CLIENT_ID",
    "776335673676-dk7od4ljhh43bio4bppf94i8ou0u9v9i.apps.googleusercontent.com",
)

# Caminhos de arquivos estáticos e bases de dados JSON
DATA_DIR: Path = BASE_DIR / "static" / "data"
ESTADOS_FILE: Path = DATA_DIR / "estados_brasil.json"
VIAGENS_FILE: Path = DATA_DIR / "viagens.json"


def carregar_estados() -> dict[str, str]:
    """Carrega o catálogo oficial das 27 UFs do Brasil diretamente do arquivo JSON."""
    with open(ESTADOS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# Mapeamento oficial das 27 Unidades Federativas do Brasil carregado do JSON
ESTADOS_BRASIL: dict[str, str] = carregar_estados()
