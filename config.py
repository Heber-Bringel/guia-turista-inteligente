# Configurações e constantes do sistema

import os

PORT: int = 8001
GEMINI_KEY: str = os.getenv("GEMINI_API_KEY", "")
GOOGLE_CLIENT_ID: str = os.getenv(
    "GOOGLE_CLIENT_ID",
    "776335673676-pvie3ppdt9oe2r6ja7jckb3vqkv523em.apps.googleusercontent.com",
)

# Mapeamento oficial das 27 Unidades Federativas do Brasil
ESTADOS_BRASIL: dict[str, str] = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}
