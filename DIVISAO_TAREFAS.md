# 📋 Divisão de Tarefas — Atividade 2: Guia do Turista Inteligente

> **Curso:** Automação Web e Python — Unidade I  
> **Atividade:** API Gateway em Flask com HTTPX & Gemini AI  
> **Repositório do grupo (fork):** [github.com/Heber-Bringel/guia-turista-inteligente](https://github.com/Heber-Bringel/guia-turista-inteligente)  
> **Repositório base do professor:** [github.com/maykolsampaio/guia-turista-inteligente](https://github.com/maykolsampaio/guia-turista-inteligente)  
> **Referência dos requisitos:** [Página da Atividade](https://maykolsampaio.github.io/cursos-maykol/cursos/automacao-web-python/unidade-1/atividade-2/)

---

## 👥 Integrantes do Grupo

| # | Nome | Papel Adaptado |
|---|------|----------------|
| 1 | **Héber Bringel** | APIs REST, Geocodificação, Google OAuth & Resiliência HTTP |
| 2 | **Douglas Leone** | Telemetria, Rotas & Inteligência Artificial (Gemini) |
| 3 | **Mikaelle Barroso** | Backend Gateway, Sessões, Idempotência & Persistência JSON |

> [!NOTE]
> A atividade foi originalmente planejada para 4 pessoas. Como o grupo conta com 3 integrantes, as responsabilidades do **Aluno 4** (JSON thread-safe, endpoint `/viagens/json` e fallbacks 404/405) foram redistribuídas entre **Héber** (fallbacks e endpoint REST) e **Mikaelle** (persistência JSON thread-safe e sanitização).

---

## 👤 Héber Bringel — APIs REST, Geocodificação & Resiliência HTTP

### 📁 Arquivos sob responsabilidade
- `services.py` — Funções de autenticação e geocodificação
- `app.py` — Tratamento global de erros (404/405) e endpoint `/viagens/json`

### 💻 Implementações de Código

#### `services.py` — Integração com Google OAuth e Open-Meteo Geocoding

```python
def verificar_token_google(client: httpx.Client, token: str) -> dict[str, Any] | None:
    """Valida o token JWT no endpoint 'https://oauth2.googleapis.com/tokeninfo'.
    Verifica se o token foi emitido para o GOOGLE_CLIENT_ID configurado.
    Retorna o payload do usuário (sub, name, email, picture) ou None se inválido.
    """
    pass

def obter_sigla_uf(admin1: str, uf_informada: str = "") -> str:
    """Converte o estado retornado pela API (admin1) para a sigla oficial de 2 letras.
    Exemplo: 'Piauí' → 'PI'.
    """
    pass

def buscar_coordenadas(
    client: httpx.Client, cidade: str, uf: str = ""
) -> tuple[float, float, str]:
    """Consulta o Open-Meteo Geocoding com filtro Brasil (country_codes=BR) e timeout=4.0s.
    Retorna a tupla (latitude, longitude, uf_oficial_detectada).
    Fallback: coordenadas aproximadas da capital da UF informada se a busca falhar.
    """
    pass
```

#### `app.py` — Endpoint REST e Fallbacks HTTP

```python
# GET /viagens/json → Retorna JSON consolidado (Content-Type: application/json)

# @app.errorhandler(404) → Redireciona rotas inexistentes suavemente para url_for('index')

# @app.errorhandler(405) → Redireciona métodos HTTP incorretos suavemente para url_for('index')
```

### 🎤 Eixos de Arguição Oral (Apresentação)

| Eixo | Tópico | O que explicar |
|------|--------|----------------|
| **Eixo 3** | Consumo de APIs REST com HTTPX & Resiliência | Por que usar `with httpx.Client() as client` (connection pooling e reaproveitamento TCP/TLS) |
| **Eixo 3** | Timeouts Defensivos | Justificar os limites de tempo nas chamadas de rede para evitar travamentos do servidor |
| **Eixo 4** | Geocodificação e Correção de UF | Consulta com `country_codes=BR` e detecção da UF real pelo campo `admin1` |
| **Eixo 4** | Validação de Token JWT | Como a credencial do Google Identity Services é validada no endpoint `/tokeninfo` conferindo o campo `aud` |
| **Eixo 5** | Endpoint REST `/viagens/json` | Retorno do JSON consolidado com `Content-Type: application/json` |
| **Eixo 5** | Tratamento Global de Erros | `@app.errorhandler(404)` e `@app.errorhandler(405)` redirecionando suavemente para `/` |

### 🧪 Testes sob responsabilidade

| Teste | Cenário | Ação ao Vivo | Resultado Esperado |
|-------|---------|-------------|-------------------|
| **Teste 1** | Autenticação Google & Modo Visitante | Fazer login com Google e como Visitante (`/auth/demo`) | Login Google valida JWT no `/tokeninfo`; Modo Visitante gera sessão isolada; Logout limpa sessão |
| **Teste 5** (parte) | Divergência de UF | Origem: Teresina / **RJ** | Geocoding corrige automaticamente para Teresina - **PI** via campo `admin1` |
| **Teste 6** | Inspeção do Endpoint JSON | Acessar `/viagens/json` | Retorna `application/json` válido com a árvore hierárquica completa |

---

## 👤 Douglas Leone — Telemetria, Rotas & Inteligência Artificial

### 📁 Arquivos sob responsabilidade
- `services.py` — Funções de clima e roteamento rodoviário
- `planejamento.py` — Geração de guia turístico com Gemini AI

### 💻 Implementações de Código

#### `services.py` — Integração com Open-Meteo Weather e OSRM

```python
def obter_clima(client: httpx.Client, lat: float, lon: float) -> dict[str, str]:
    """Consulta o Open-Meteo Forecast e retorna temperatura (°C), umidade (%) e vento (km/h)."""
    pass

def obter_percurso(
    client: httpx.Client, lat_o: float, lon_o: float, lat_d: float, lon_d: float
) -> dict[str, str]:
    """Consulta o OSRM e calcula distância em km e duração de viagem de carro.
    Em caso de trajetos sem estradas (ex: ilhas), retorna dicionário com fallback descritivo.
    """
    pass
```

#### `planejamento.py` — Integração com Gemini AI e Fallback

```python
def limpar_formato_texto(texto: str) -> str:
    """Remove marcações residuais de markdown (** ou *) e saudações, mantendo apenas emojis."""
    pass

def obter_guia_destino_com_diagnostico(destino: str) -> tuple[str, dict[str, Any]]:
    """Invoca o modelo 'gemini-3.6-flash' com timeout de 6.0s em ThreadPoolExecutor.
    Em caso de timeout, chave inválida ou ausência de cota, aciona automaticamente
    o gerador de contingência com roteiro estruturado em texto puro com emojis.
    Retorna a tupla (texto_guia, diagnostico_metadados).
    """
    pass

def obter_guia_destino(destino: str) -> str:
    """Wrapper utilitário que retorna apenas o texto do guia."""
    texto, _ = obter_guia_destino_com_diagnostico(destino)
    return texto
```

### 🎤 Eixos de Arguição Oral (Apresentação)

| Eixo | Tópico | O que explicar |
|------|--------|----------------|
| **Eixo 1** | Tipagem Estática & Qualidade de Código | Assinaturas modernas Python 3.10+ (`tuple[float, float, str]`, `dict[str, Any] | None`), validação com `ruff check .` e `mypy .` |
| **Eixo 1** | Telemetria de Clima e Rotas | Consumo das APIs Open-Meteo Weather e OSRM; conversão de metros → km (`round(m/1000, 1)`) e segundos → horas/minutos |
| **Eixo 6** | Engenharia de Prompt | Restrições no prompt para forçar respostas em texto puro com emojis, sem asteriscos ou Markdown |
| **Eixo 6** | Sanitização Regex & Fallback da IA | Função `limpar_formato_texto()`, isolamento em `ThreadPoolExecutor(timeout=6.0s)` e disparo do guia de contingência |

### 🧪 Testes sob responsabilidade

| Teste | Cenário | Ação ao Vivo | Resultado Esperado |
|-------|---------|-------------|-------------------|
| **Teste 2** | Fallback da IA Gemini | Definir `GEMINI_API_KEY="CHAVE_INVALIDA"` e gerar uma viagem | Sem erro 500; card exibe roteiro estruturado de contingência em texto puro com emojis |
| **Teste 5** (parte) | Destino sem estrada rodoviária | Destino: Fernando de Noronha / PE | OSRM exibe "Sem rota direta" e "Considere voos ou barcos" |

---

## 👤 Mikaelle Barroso — Backend Gateway, Sessões, Idempotência & Persistência JSON

### 📁 Arquivos sob responsabilidade
- `app.py` — Rotas principais, sessões, lock de concorrência, persistência JSON e sanitização de entradas

### 💻 Implementações de Código

#### `app.py` — Rotas, Sessões e Idempotência

```python
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "chave-secreta-de-sessao")
lock_requisicoes = threading.Lock()

# Rotas a implementar:
# 1. GET  /                     → Renderiza index.html com lista de viagens do usuário logado
# 2. POST /auth/google/callback → Recebe credencial JWT do frontend, valida e grava session['usuario']
# 3. GET  /auth/demo            → Cria sessão volátil em memória para 'Viajante Convidado'
# 4. GET  /auth/logout          → Limpa session e dados temporários de visitante
# 5. POST /viagens/criar        → Orquestra chamadas com lock_requisicoes e aplica Padrão PRG (HTTP 302)
# 6. POST /viagens/deletar/<id> → Remove o roteiro específico do usuário logado
```

#### `app.py` — Persistência JSON Thread-Safe e Sanitização

```python
lock_arquivo_json = threading.Lock()

def sanitizar_entrada(texto: str, max_len: int = 80) -> str:
    """Remove tags HTML (regex r'<[^>]*>') e caracteres perigosos de controle."""
    pass

def carregar_dados_viagens_json() -> dict[str, Any]:
    """Lê static/data/viagens.json de forma segura com lock_arquivo_json."""
    pass

def salvar_dados_viagens_json(dados_completos: dict[str, Any]) -> None:
    """Persiste static/data/viagens.json com lock_arquivo_json e indentação de 2 espaços."""
    pass
```

### 🎤 Eixos de Arguição Oral (Apresentação)

| Eixo | Tópico | O que explicar |
|------|--------|----------------|
| **Eixo 2** | Ciclo de Vida HTTP (POST vs GET) | Diferença semântica entre a rota `/` (GET idempotente) e `/viagens/criar` (POST não-idempotente) |
| **Eixo 2** | Padrão Post/Redirect/Get (PRG) | Por que a rota de criação responde com HTTP 302 redirecionando para a home (evitando reenvio acidental com F5) |
| **Eixo 2** | Idempotência & Bloqueio de Concorrência | Frontend (desabilitação do botão com spinner) + backend (`threading.Lock`) evitam cliques duplos |
| **Eixo 2** | Segurança de Sessão | Como `session["usuario"]` persiste o usuário autenticado via cookies criptografados e como funciona o Modo Visitante |
| **Eixo 5** | Anatomia do Payload JSON | Estrutura hierárquica do arquivo `static/data/viagens.json` (nó raiz com metadados, provedores e nós por usuário) |
| **Eixo 5** | Leitura e Escrita Thread-Safe | Uso do `threading.Lock()` para prevenir corrupção de dados por concorrência; diferença entre `json.load/json.dump` e `json.loads/json.dumps` |
| **Eixo 5** | Navegação Defensiva | Uso de `.get()` encadeado com valores padrão para prevenir exceções `KeyError` ao consumir dados aninhados |

### 🧪 Testes sob responsabilidade

| Teste | Cenário | Ação ao Vivo | Resultado Esperado |
|-------|---------|-------------|-------------------|
| **Teste 3** | Métodos HTTP Incorretos (405) e Rotas 404 | Acessar rota inexistente ou acessar `/viagens/criar` via GET | Flask intercepta e redireciona suavemente para `/` sem exibir página de erro |
| **Teste 4** | Bloqueio de Cliques Duplos (Idempotência) | Submeter formulário e disparar cliques rápidos sucessivos | Frontend desabilita botão com spinner; Backend descarta requisições repetidas via `lock_requisicoes` |

---

## 📂 Estrutura do Payload JSON (Referência)

O arquivo `static/data/viagens.json` manipulado por Mikaelle e preenchido pela orquestração da equipe deve respeitar o schema abaixo:

```json
{
  "versao_schema": "1.0",
  "atualizado_em": "2026-09-19T17:00:00.000000",
  "total_usuarios": 1,
  "total_roteiros": 1,
  "provedores": {
    "geocoding": "Open-Meteo Geocoding API",
    "previsao_tempo": "Open-Meteo Forecast API",
    "roteamento": "OSRM Routing Engine",
    "inteligencia_artificial": "Google Gemini (gemini-3.6-flash)"
  },
  "usuarios": {
    "<user_id>": {
      "perfil": { "id": "...", "nome": "...", "email": "...", "foto": "..." },
      "metadados": { "total_roteiros": 1, "criado_em": "...", "atualizado_em": "..." },
      "roteiros": [
        {
          "id": "fdf022a3",
          "criado_em": "...",
          "origem": "Teresina - PI",
          "destino": "Brasília - DF",
          "geolocalizacao": {
            "origem": { "cidade": "Teresina", "uf": "PI", "latitude": -5.089, "longitude": -42.801 },
            "destino": { "cidade": "Brasília", "uf": "DF", "latitude": -15.779, "longitude": -47.929 }
          },
          "telemetria": {
            "clima": { "temperatura": "28.5 °C", "umidade": "35%", "vento": "12.0 km/h" },
            "percurso": { "distancia": "1674.6 km", "tempo": "21h 38min de carro", "modal": "carro" }
          },
          "dicas_destino": "🏛️ PONTOS TURÍSTICOS PRINCIPAIS\n...",
          "metadados": {
            "status_requisicao": "sucesso",
            "status_servicos": {
              "geocoding_origem": { "status": "sucesso", "mensagem": "Coordenadas localizadas" },
              "inteligencia_artificial": { "status": "sucesso", "modelo": "gemini-3.6-flash", "fallback_utilizado": false }
            }
          }
        }
      ]
    }
  }
}
```

---

## 📊 Resumo dos Critérios de Avaliação

| Integrante | Eixos Avaliados | Nota Máxima |
|-----------|-----------------|-------------|
| **Héber Bringel** | Eixo 3 (HTTPX & Resiliência), Eixo 4 (JWT & Geocoding), Eixo 5 (JSON endpoint & 404/405) | 10,0 |
| **Douglas Leone** | Eixo 1 (Tipagem & Qualidade), Eixo 6 (IA Gemini, Prompt & Fallback) | 10,0 |
| **Mikaelle Barroso** | Eixo 2 (HTTP, PRG & Idempotência), Eixo 5 (JSON thread-safe, payload & `.get()`) | 10,0 |

> [!IMPORTANT]
> A avaliação é **individual e comparativa**: o professor rankeia o desempenho de cada integrante em relação aos pares de mesma função nos outros grupos. A nota final do grupo é a média aritmética simples das 3 notas individuais.

---

## 🚀 Instruções de Setup (Todos os Integrantes)

```bash
# 1. Clonar o repositório do grupo
git clone https://github.com/Heber-Bringel/guia-turista-inteligente.git
cd guia-turista-inteligente

# 2. Criar e ativar o ambiente virtual
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 3. Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente — copie o exemplo e edite com sua chave Gemini
# Linux/macOS:
cp .env.example .env
# Windows (PowerShell):
Copy-Item .env.example .env

# 5. Preparar o arquivo de dados inicial
# Linux/macOS:
cp static/data/viagens.json.example static/data/viagens.json
# Windows (PowerShell):
Copy-Item static\data\viagens.json.example static\data\viagens.json

# 6. Carregar as variáveis e iniciar o servidor
# Windows (PowerShell):
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}
python app.py
# Acesse: http://localhost:8001
```

> ⚠️ Nunca commite o arquivo `.env` — ele está no `.gitignore`!

---

*Documento gerado em 22/09/2026 • Atividade 2 — Guia do Turista Inteligente*
