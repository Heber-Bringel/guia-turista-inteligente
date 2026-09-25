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

## 🏗️ Arquitetura do Projeto (MVC)

O código foi organizado em camadas. As funções e os eixos de arguição abaixo continuam os mesmos; mudou apenas **onde** cada trecho mora:

| Camada | Local | Quem |
|--------|-------|------|
| **Model** | `models/viagem_repository.py` (JSON thread-safe com `RLock`, visitantes em memória) | Mikaelle |
| **Controller** | `controllers/` — `main`, `auth`, `viagem` (PRG + idempotência), `api` (`/viagens/json` e erros 404/405/500), `validacao` | Mikaelle e Héber |
| **View** | `templates/index.html` e `static/` | — |
| **Services** | `services/` — `google_auth`, `geocoding` (Héber) · `clima`, `rotas`, `gemini`, `sanitizacao`, `contingencia` (Douglas) | Héber e Douglas |

`app.py` ficou apenas com a fábrica `create_app()` e o registro dos Blueprints.

---

## 👤 Héber Bringel — APIs REST, Geocodificação & Resiliência HTTP

### 📁 Arquivos sob responsabilidade
- `services/google_auth.py` e `services/geocoding.py` — Funções de autenticação e geocodificação
- `controllers/api_controller.py` — Tratamento global de erros (404/405/500) e endpoint `/viagens/json`

### 💻 Implementações de Código

#### `services/google_auth.py` e `services/geocoding.py` — Integração com Google OAuth e Open-Meteo Geocoding

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

#### `controllers/api_controller.py` — Endpoint REST e Fallbacks HTTP

```python
# GET /viagens/json → Retorna JSON consolidado (Content-Type: application/json)

# @api_bp.app_errorhandler(404) → Redireciona rotas inexistentes suavemente para url_for('main.index')

# @api_bp.app_errorhandler(405) → Redireciona métodos HTTP incorretos suavemente para url_for('main.index')
```

### 🎤 Eixos de Arguição Oral (Apresentação)

| Eixo | Tópico | Resposta |
|------|--------|----------------|
| **Eixo 3** | Consumo de APIs REST com HTTPX & Resiliência | Chamadas soltas (`httpx.get`) criam um cliente por requisição e refazem o handshake TCP e TLS a cada vez. O `with httpx.Client() as client` mantém um **pool de conexões keep-alive** por host e reaproveita a conexão (as duas buscas de geocoding vão ao mesmo host); ao sair do bloco fecha tudo, mesmo se houver exceção. O cliente é passado como parâmetro para cada função de serviço. |
| **Eixo 3** | Timeouts Defensivos | Uma API lenta prende a thread do servidor e o usuário fica esperando. Por isso toda chamada tem timeout explícito e, se falhar, devolve um **fallback** (capital da UF, `N/D`, “Sem rota direta”, guia de contingência): **4 s** em geocoding, clima e `tokeninfo`; **6 s** no OSRM e no Gemini. No navegador o botão é liberado sozinho após 12 s. |
| **Eixo 4** | Geocodificação e Correção de UF | A busca vai só com o nome da cidade e o filtro de país **`countryCode=BR`** (evita homônimos, como a Teresina da Polônia; a API ignora o nome `country_codes`). O `admin1` vem como nome do estado, e `obter_sigla_uf` remove acentos e converte `"Piauí"` em `"PI"`. Fica o candidato da UF digitada ou, se nenhum bater, o primeiro: assim *Teresina / RJ* vira *Teresina - PI*. |
| **Eixo 4** | Validação de Token JWT | O navegador devolve a `credential` (um JWT) e o servidor a envia ao endpoint oficial `oauth2.googleapis.com/tokeninfo`, onde o Google valida assinatura e expiração. Depois conferimos se o campo **`aud`** é igual ao nosso `GOOGLE_CLIENT_ID`, o que garante que o token foi emitido **para o nosso app**. Só então lemos `sub`, `name`, `email` e `picture` e abrimos a sessão; qualquer falha devolve `None`. |
| **Eixo 5** | Endpoint REST `/viagens/json` | `GET /viagens/json` (com os aliases `/api/viagens` e `/api/viagens/json`) responde com `jsonify(...)`, ou seja, `Content-Type: application/json`. A função `montar_payload_consolidado` lê o `viagens.json`, mescla os roteiros do visitante (que só existem em memória) e recalcula os totais. |
| **Eixo 5** | Tratamento Global de Erros | Os handlers de **404** (rota inexistente) e **405** (método não permitido, como um GET em `/viagens/criar`) respondem com redirecionamento 302 para `/`, em vez de mostrar página de erro. Com Blueprint usamos `@api_bp.app_errorhandler`, o equivalente de `@app.errorhandler`: vale para o aplicativo inteiro. |

> Explicação completa e trechos de código de cada ponto: [Roteiro de Apresentação](README.md#-roteiro-de-apresentação).

### 🧪 Testes sob responsabilidade

| Teste | Cenário | Ação ao Vivo | Resultado Esperado |
|-------|---------|-------------|-------------------|
| **Teste 1** | Autenticação Google & Modo Visitante | Fazer login com Google e como Visitante (`/auth/demo`) | Login Google valida JWT no `/tokeninfo`; Modo Visitante gera sessão isolada; Logout limpa sessão |
| **Teste 5** (parte) | Divergência de UF | Origem: Teresina / **RJ** | Geocoding corrige automaticamente para Teresina - **PI** via campo `admin1` |
| **Teste 6** | Inspeção do Endpoint JSON | Acessar `/viagens/json` | Retorna `application/json` válido com a árvore hierárquica completa |

---

## 👤 Douglas Leone — Telemetria, Rotas & Inteligência Artificial

### 📁 Arquivos sob responsabilidade
- `services/clima.py` e `services/rotas.py` — Funções de clima e roteamento rodoviário
- `services/gemini.py`, `services/sanitizacao.py` e `services/contingencia.py` — Geração de guia turístico com Gemini AI

### 💻 Implementações de Código

#### `services/clima.py` e `services/rotas.py` — Integração com Open-Meteo Weather e OSRM

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

#### `services/gemini.py`, `services/sanitizacao.py` e `services/contingencia.py` — Integração com Gemini AI e Fallback

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

| Eixo | Tópico | Resposta |
|------|--------|----------------|
| **Eixo 1** | Tipagem Estática & Qualidade de Código | Usamos `tuple[...]`, `dict[...]` e `list[...]` direto (PEP 585) e `X \| None` no lugar de `Optional` (PEP 604). `tuple[float, float, str]` é uma tupla de tamanho fixo (latitude, longitude, UF); `dict[str, Any] \| None` é o payload do Google ou `None` se o token for inválido. O Python ignora as anotações ao rodar: quem as verifica é o **mypy**, e o **ruff** aponta más práticas. Resultado: `ruff check .` → `All checks passed!` e `mypy .` → `Success`. |
| **Eixo 1** | Telemetria de Clima e Rotas | A Open-Meteo Forecast (sem chave, 4 s) traz temperatura, umidade e vento. O OSRM (6 s) calcula a rota de carro, com a **longitude primeiro** na URL, e se o destino ficar a mais de 10 km de uma estrada (ilhas) devolve “Sem rota direta”. Conversões: `round(m/1000, 1)` para km; `horas = s // 3600` e `minutos = round((s % 3600) / 60)`, com ajuste quando dá 60, formatando `2h 30min de carro`. |
| **Eixo 6** | Engenharia de Prompt | O front exibe o texto cru e não interpreta Markdown, então o prompt define persona, 4 títulos fixos com emoji, 1 a 2 frases por item e um bloco de **regras de formato**: proíbe `*`, `**`, `#`, `_`, crases, saudações e despedidas, e manda começar pelo primeiro título. A chamada usa `thinking_budget=0` e `max_output_tokens=650` para caber no tempo limite. |
| **Eixo 6** | Sanitização Regex & Fallback da IA | `limpar_formato_texto()` remove crases, converte listas em `•` e tira títulos `#`, negrito, itálico, a saudação da primeira linha e a despedida da última (a ordem importa). O Gemini roda numa thread com `future.result(timeout=6.0)` e o executor é encerrado com `shutdown(wait=False)`, então a resposta sai em 6 s. Chave vazia, timeout ou qualquer exceção acionam o **guia de contingência** (base curada ou guia genérico), com o badge “Modo Contingência”. |

> Explicação completa e trechos de código de cada ponto: [Roteiro de Apresentação](README.md#-roteiro-de-apresentação).

### 🧪 Testes sob responsabilidade

| Teste | Cenário | Ação ao Vivo | Resultado Esperado |
|-------|---------|-------------|-------------------|
| **Teste 2** | Fallback da IA Gemini | Definir `GEMINI_API_KEY="CHAVE_INVALIDA"` e gerar uma viagem | Sem erro 500; card exibe roteiro estruturado de contingência em texto puro com emojis |
| **Teste 5** (parte) | Destino sem estrada rodoviária | Destino: Fernando de Noronha / PE | OSRM exibe "Sem rota direta" e "Considere voos ou barcos" |

---

## 👤 Mikaelle Barroso — Backend Gateway, Sessões, Idempotência & Persistência JSON

### 📁 Arquivos sob responsabilidade
- `controllers/` (`main`, `auth`, `viagem`) e `models/viagem_repository.py` — Rotas principais, sessões, lock de concorrência, persistência JSON e sanitização de entradas (`controllers/validacao.py`)

### 💻 Implementações de Código

#### `controllers/` — Rotas, Sessões e Idempotência (Blueprints do Flask)

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

#### `models/viagem_repository.py` e `controllers/validacao.py` — Persistência JSON Thread-Safe e Sanitização

```python
lock_arquivo_json = threading.RLock()

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

| Eixo | Tópico | Resposta |
|------|--------|----------------|
| **Eixo 2** | Ciclo de Vida HTTP (POST vs GET) | `GET /` só lê e renderiza: é seguro e **idempotente** (pode repetir, cachear e favoritar). `POST /viagens/criar` cria um roteiro novo a cada execução, então **não é idempotente**; por isso só aceita POST, com os dados no corpo, e um GET nessa rota cai no 405 e volta para `/`. |
| **Eixo 2** | Padrão Post/Redirect/Get (PRG) | Se o POST renderizasse a página, o F5 reenviaria o formulário e duplicaria o roteiro. No PRG o servidor processa o POST e responde **`302 Found`** para `/`; o navegador faz um GET, e o F5 só repete esse GET. Vale para criar, excluir e login. |
| **Eixo 2** | Idempotência & Bloqueio de Concorrência | São duas camadas. No front, a flag `submetido` desabilita o botão (com spinner) e cancela o segundo envio. No back, que é quem realmente garante, a chave `usuário\|origem\|uf\|destino\|uf` é registrada em `requisicoes_ativas` e `requisicoes_recentes` (janela de 10 s), e o `threading.Lock` torna o “verificar e registrar” atômico. Com 5 POSTs simultâneos, só 1 roteiro é criado. |
| **Eixo 2** | Segurança de Sessão | `session["usuario"]` fica em um **cookie assinado** com a `SECRET_KEY` (HMAC): o conteúdo é legível (base64), mas não pode ser alterado sem a chave. A cada requisição o Flask confere a assinatura e reconstrói a sessão. No **Modo Visitante** (`/auth/demo`) o id é `visitante-<uuid>`, os roteiros ficam só em memória (nunca no JSON) e o logout apaga tudo. |
| **Eixo 5** | Anatomia do Payload JSON | Nó raiz com `versao_schema`, `atualizado_em`, `total_usuarios` e `total_roteiros`; catálogo `provedores`; e `usuarios`, indexado pelo id do usuário. Cada usuário tem `perfil`, `metadados` e a lista `roteiros`; cada roteiro traz `geolocalizacao`, `telemetria` (clima e percurso), `dicas_destino`, `diagnostico_ia` e `metadados.status_servicos`. Visitantes não aparecem no arquivo. |
| **Eixo 5** | Leitura e Escrita Thread-Safe | Várias threads usam o mesmo arquivo; sem lock, duas requisições leem a mesma versão e a última a gravar apaga a da outra. O `RLock` (reentrante, porque a função que segura o lock chama outras que também o adquirem) envolve o ciclo inteiro *ler → alterar → salvar*. `json.load/json.dump` trabalham com **arquivo**; `json.loads/json.dumps`, com **string**. O teste de 10 gravações simultâneas salva as 10. |
| **Eixo 5** | Navegação Defensiva | `dados["usuarios"][id]["roteiros"]` lança `KeyError` se algum nível faltar. Com `.get(chave, padrão)` encadeado (`dados.get("usuarios", {})` → `usuarios.get(id, {})` → `usuario.get("roteiros")`) e `isinstance` a cada nível, um dado ausente ou corrompido vira uma lista vazia e a página não quebra. Também aceita a chave legada `viagens`. |

> Explicação completa e trechos de código de cada ponto: [Roteiro de Apresentação](README.md#-roteiro-de-apresentação).

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
