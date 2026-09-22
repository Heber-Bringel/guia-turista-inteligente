# 🇧🇷 Guia do Turista Inteligente

> Atividade 2 — Automação Web e Python | Unidade I  
> **Fork do grupo:** [Heber-Bringel/guia-turista-inteligente](https://github.com/Heber-Bringel/guia-turista-inteligente)  
> **Repositório base do professor:** [maykolsampaio/guia-turista-inteligente](https://github.com/maykolsampaio/guia-turista-inteligente)

Aplicação web desenvolvida com **Flask** e Python moderno para orquestração de APIs externas com autenticação via **Google Identity Services (OAuth JWT)**, gerando roteiros de viagem com dados meteorológicos, cálculo de percurso rodoviário e guia turístico com inteligência artificial (Google Gemini AI).

---

## 👥 Grupo

| Integrante | Papel |
|---|---|
| **Héber Bringel** | APIs REST, Geocodificação, Google OAuth & Resiliência HTTP |
| **Douglas Leone** | Telemetria, Rotas (OSRM) & Inteligência Artificial (Gemini) |
| **Mikaelle Barroso** | Backend Gateway, Sessões, Idempotência & Persistência JSON |

> Consulte o arquivo [DIVISAO_TAREFAS.md](./DIVISAO_TAREFAS.md) para o detalhamento completo das responsabilidades de cada integrante.

---

## 🚀 Como Executar Localmente

### 1. Clonar o repositório

```bash
git clone https://github.com/Heber-Bringel/guia-turista-inteligente.git
cd guia-turista-inteligente
```

---

### 2. Criar e ativar o ambiente virtual

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

---

### 3. Instalar as dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Configurar as variáveis de ambiente

Copie o arquivo de exemplo e preencha com suas chaves:

```bash
# Linux / macOS
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

Edite o `.env` e preencha a sua `GEMINI_API_KEY`:

```env
GEMINI_API_KEY=SUA_CHAVE_AQUI
GOOGLE_CLIENT_ID=776335673676-dk7od4ljhh43bio4bppf94i8ou0u9v9i.apps.googleusercontent.com
PORT=8001
SECRET_KEY=guia-turista-secret-key-2026-python
```

> 🔑 **Obtenha sua chave Gemini gratuitamente em:** [aistudio.google.com](https://aistudio.google.com)

> ⚠️ **Nunca commite o arquivo `.env` — ele está no `.gitignore`!**

---

### 5. Preparar o arquivo de dados

```bash
# Linux / macOS
cp static/data/viagens.json.example static/data/viagens.json

# Windows (PowerShell)
Copy-Item static\data\viagens.json.example static\data\viagens.json
```

---

### 6. Carregar as variáveis e iniciar o servidor

**Linux / macOS:**
```bash
export $(cat .env | xargs)
python app.py
```

**Windows (PowerShell):**
```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}
python app.py
```

Acesse no navegador: 👉 **`http://localhost:8001`**

---

## 📂 Estrutura do Projeto

```text
guia-turista-inteligente/
├── app.py                  # [A IMPLEMENTAR] Rotas Flask, sessões, persistência JSON e fallbacks
├── config.py               # Constantes, portas, chaves e catálogo de UFs
├── services.py             # [A IMPLEMENTAR] Integrações HTTPX: Google OAuth, Geocoding, Clima e OSRM
├── planejamento.py         # [A IMPLEMENTAR] Gemini AI: geração de guia turístico e fallback
├── templates/
│   └── index.html          # Template Jinja2 (SSR, Google Login, Formulário e Cards)
├── static/
│   ├── css/style.css       # Estilização responsiva mobile-first
│   ├── js/app.js           # Accordion dos cards e bloqueio de múltiplos cliques
│   └── data/
│       ├── estados_brasil.json      # Catálogo oficial das 27 UFs do Brasil
│       ├── viagens.json             # Base de dados em runtime (não versionada)
│       └── viagens.json.example    # Estrutura inicial vazia (template)
├── .env.example            # Template de variáveis de ambiente
├── .gitignore              # Ignora .env, .venv, cache e dados de runtime
├── DIVISAO_TAREFAS.md      # Divisão de responsabilidades do grupo
├── requirements.txt        # Dependências Python
└── README.md               # Este arquivo
```

---

## 🌐 APIs Externas Utilizadas

| # | API | Endpoint | Chave necessária? |
|---|-----|----------|:-----------------:|
| 1 | Google OAuth2 | `https://oauth2.googleapis.com/tokeninfo` | Não (usa GOOGLE_CLIENT_ID) |
| 2 | Open-Meteo Geocoding | `https://geocoding-api.open-meteo.com/v1/search` | ❌ Gratuita |
| 3 | Open-Meteo Weather | `https://api.open-meteo.com/v1/forecast` | ❌ Gratuita |
| 4 | OSRM Routing Machine | `https://router.project-osrm.org/route/v1/driving/` | ❌ Gratuita |
| 5 | Google Gemini AI | SDK `google-genai` (`gemini-3.6-flash`) | ✅ `GEMINI_API_KEY` |

---

## 🧪 Qualidade de Código

```bash
# Linter e formatação (PEP 8)
ruff check . --fix

# Checagem estática de tipos
mypy app.py services.py planejamento.py config.py
```
