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

> 🎤 **Vai apresentar?** Veja o [Roteiro de Apresentação](#-roteiro-de-apresentação): para cada ponto de cada integrante há a resposta pronta e o trecho de código correspondente.

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
├── app.py                  # Fábrica da aplicação Flask (create_app) e registro dos controllers
├── models/                 # M — Model
│   └── viagem_repository.py    # Persistência JSON thread-safe (RLock) e visitantes em memória
├── controllers/            # C — Controllers (Blueprints do Flask)
│   ├── main_controller.py      # GET /  (página principal)
│   ├── auth_controller.py      # Login Google, modo visitante e logout
│   ├── viagem_controller.py    # Criar/deletar roteiros (PRG + idempotência)
│   ├── api_controller.py       # GET /viagens/json e handlers 404/405/500
│   └── validacao.py            # Sanitização de entradas
├── tests/
│   └── test_fluxo_web.py       # Testes do fluxo web (offline, APIs externas simuladas)
├── config.py               # Constantes, portas, chaves e catálogo de UFs
├── services/               # Serviços: integrações com APIs externas
│   ├── google_auth.py          # Validação do token JWT do Google (Aluno 1)
│   ├── geocoding.py            # Open-Meteo Geocoding, UF oficial e fallback de capitais (Aluno 1)
│   ├── clima.py                # Open-Meteo Forecast: temperatura, umidade e vento (Aluno 2)
│   ├── rotas.py                # OSRM: distância, duração e detecção de destinos sem estrada (Aluno 2)
│   ├── gemini.py               # Gemini AI: prompt, timeout de 6s em thread e fallback (Aluno 2)
│   ├── sanitizacao.py          # Regex que remove Markdown, saudações e despedidas (Aluno 2)
│   └── contingencia.py         # Guia de contingência em texto puro com emojis (Aluno 2)
├── static/img/visitante.svg    # Avatar padrão do modo visitante
├── templates/              # V — View
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
mypy .

# Testes do fluxo web (offline)
python -m unittest discover -s tests -v
```

---

## 🎤 Roteiro de Apresentação

Guia para a apresentação oral. Para cada ponto que o integrante precisa explicar há **a pergunta**, **a resposta pronta para falar** e **o trecho do código** (com arquivo e linha, clicável no GitHub) para abrir na hora.

O projeto tem 3 integrantes, então o quarto papel do enunciado (Aluno 4) foi dividido conforme o [`DIVISAO_TAREFAS.md`](DIVISAO_TAREFAS.md):

| Integrante | Papéis do enunciado | Pontos que explica |
|---|---|---|
| [👤 Héber Bringel](#-héber-bringel--apis-rest-geocodificação-e-autenticação) | Aluno 1 + *Tratamento Global de Erros* do Aluno 4 | HTTPX e pooling · Timeouts · Geocodificação e UF · Token JWT · Erros 404/405 e `/viagens/json` |
| [👤 Douglas Leone](#-douglas-leone--telemetria-rotas-e-inteligência-artificial) | Aluno 2 | Tipagem e qualidade · Clima e rotas · Engenharia de prompt · Regex e fallback da IA |
| [👤 Mikaelle Barroso](#-mikaelle-barroso--backend-gateway-sessões-idempotência-e-persistência-json) | Aluno 3 + Persistência JSON do Aluno 4 | GET × POST · PRG · Idempotência · Sessão · Payload JSON · Thread-safe · `.get()` |

**Arquitetura em uma frase (vale para qualquer pergunta):** o projeto segue MVC. O *Controller* (`controllers/`) recebe a requisição HTTP, o *Model* (`models/`) persiste os dados, a *View* (`templates/`) mostra o resultado e a camada de *Services* (`services/`) conversa com as APIs externas.

**Testes que comprovam o que é dito abaixo:** `python -m unittest discover -s tests -v` (16 testes, rodam sem internet) e `python testar_douglas.py` (clima, rotas, regex e fallback da IA).

---

### 👤 Héber Bringel — APIs REST, Geocodificação e Autenticação

#### 🌐 1. Consumo com HTTPX & Connection Pooling

> **Pergunta do professor:** Explicar por que instanciar o cliente com `with httpx.Client() as client` é mais eficiente do que chamadas soltas (reaproveitamento de conexões TCP/TLS).

**Resposta (o que falar):**

- Uma chamada solta (`httpx.get(...)`) cria e descarta um cliente a cada requisição, então **cada chamada refaz o handshake TCP e o TLS** (várias idas e voltas na rede antes de trafegar qualquer dado).
- O `httpx.Client()` mantém um **pool de conexões keep-alive** por servidor: a segunda chamada ao mesmo host reaproveita a conexão que já está aberta.
- Neste projeto, criar um roteiro faz várias chamadas com o **mesmo** cliente: geocoding da origem, geocoding do destino, clima e rota. As duas buscas de geocoding vão ao mesmo host (`geocoding-api.open-meteo.com`) e reaproveitam a conexão; clima e OSRM são outros hosts, cada um com sua conexão no pool.
- O `with` garante que o pool seja **fechado** ao sair do bloco, mesmo se acontecer uma exceção (não vazam conexões abertas).
- O cliente é passado como parâmetro (`client: httpx.Client`) para cada função de serviço: nenhuma função cria cliente próprio, e isso também facilita simular a rede nos testes.

**No código:** [`controllers/viagem_controller.py:48-59`](controllers/viagem_controller.py#L48-L59) — um único cliente atende as duas buscas de geocoding (e depois clima e rota)

```python
    with httpx.Client() as client:
        lat_origem, lon_origem, uf_origem_det = buscar_coordenadas(
            client,
            origem_cidade,
            origem_uf,
        )

        lat_destino, lon_destino, uf_destino_det = buscar_coordenadas(
            client,
            destino_cidade,
            destino_uf,
        )
```

**No código:** [`controllers/auth_controller.py:23-24`](controllers/auth_controller.py#L23-L24) — mesmo padrão na validação do token Google

```python
    with httpx.Client() as client:
        dados_usuario = verificar_token_google(client, token)
```

**No código:** [`services/geocoding.py:89-91`](services/geocoding.py#L89-L91) — a função recebe o cliente como parâmetro

```python
def buscar_coordenadas(
    client: httpx.Client, cidade: str, uf: str = ""
) -> tuple[float, float, str]:
```

**Se perguntarem:** *“Por que não um cliente global?”* — Poderia, mas aqui o escopo do `with` é a própria requisição: é simples, não compartilha estado entre threads e sempre libera as conexões.


#### ⏱️ 2. Timeouts Defensivos

> **Pergunta do professor:** Justificar os limites estritos de tempo configurados nas chamadas de rede para evitar travamentos do servidor.

**Resposta (o que falar):**

- A rede é a parte imprevisível do sistema. O servidor Flask atende cada requisição em uma thread: se uma API externa demorar, **essa thread e o usuário ficam presos esperando**.
- Por isso toda chamada tem timeout explícito e cada função de serviço **captura a falha e devolve um fallback** (coordenadas da capital, `N/D`, “Sem rota direta”, guia de contingência). O usuário recebe uma resposta degradada, nunca uma página quebrada.
- Os valores seguem o perfil de cada API: **4 s** para as consultas simples (geocoding, clima e `tokeninfo` do Google), **6 s** para o OSRM (o servidor público é mais lento e calcula a rota) e **6 s** para o Gemini (LLM), este isolado em uma thread.
- Pior caso somado em uma criação de roteiro: 4 + 4 + 4 + 6 + 6 = 24 s. No navegador o botão é liberado sozinho após 12 s (`app.js`), então a tela nunca fica travada para sempre.
- O `httpx` já tem um timeout padrão de 5 s, mas definir o valor de forma explícita documenta a intenção e permite ajustar por serviço.

**No código:** [`services/geocoding.py:109`](services/geocoding.py#L109) — geocoding: 4 s

```python
        resposta = client.get(url, params=params, timeout=4.0)
```

**No código:** [`services/google_auth.py:17-21`](services/google_auth.py#L17-L21) — tokeninfo do Google: 4 s

```python
        resposta = client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": token},
            timeout=4.0,
        )
```

**No código:** [`services/clima.py:30`](services/clima.py#L30) — clima: 4 s

```python
        resposta = client.get(url, params=params, timeout=4.0)
```

**No código:** [`services/rotas.py:29`](services/rotas.py#L29) — OSRM: 6 s

```python
        resposta = client.get(url, params=params, timeout=6.0)
```

**No código:** [`services/gemini.py:124`](services/gemini.py#L124) — Gemini: 6 s, via `future.result(timeout=...)`

```python
        texto_bruto, modelo_utilizado = future.result(timeout=6.0)
```


#### 📍 3. Geocodificação e Correção de UF

> **Pergunta do professor:** Explicar a consulta com filtro Brasil (`country_codes=BR`) e a detecção da UF real através do campo `admin1` retornado pela API.

**Resposta (o que falar):**

- O geocoding é o **Open-Meteo Geocoding API** (gratuito, sem chave). Ele recebe o **nome da cidade** e devolve uma lista de candidatos com latitude, longitude e o estado no campo **`admin1`** (por exemplo, `"Piauí"`).
- O **filtro de país** restringe a busca ao Brasil. Sem ele, homônimos de outros países aparecem: existe uma *Teresina* na Polônia e uma *Santa Maria* nos EUA. Também usamos `language=pt` e `count=10`.
- ⚠️ **Detalhe que vale citar:** o enunciado fala em `country_codes=BR`, mas ao testar a API real vimos que ela **ignora esse nome** (a busca ainda devolvia a Teresina polonesa). O parâmetro que ela respeita é **`countryCode=BR`**, que é o que o código usa. O conceito é o mesmo: filtrar por código de país ISO.
- A busca vai **só com o nome da cidade**: juntar a UF no texto (`"Teresina PI"`) não retorna nenhum resultado, e o sistema cairia no fallback.
- O `admin1` vem como **nome do estado**, não como sigla. A função `obter_sigla_uf` normaliza o texto (remove acentos com `unicodedata`, minúsculas) e procura no catálogo `ESTADOS_BRASIL` (`static/data/estados_brasil.json`), convertendo `"Piauí"` em `"PI"`.
- **Escolha do candidato:** `_escolher_resultado` percorre os candidatos e pega o que **pertence à UF digitada** (assim *Santa Maria / RS* e *Santa Maria / PB* são cidades diferentes). Se nenhum candidato estiver naquela UF, usa o primeiro, que é o mais relevante para a API.
- **Correção de UF:** se o usuário informar *Teresina / RJ*, nenhum candidato está no RJ, então vale o primeiro (Teresina, `admin1 = "Piauí"`) e a UF detectada é **PI**. O controller usa a UF detectada e não a digitada (`uf_origem_det or origem_uf`), e o roteiro fica *Teresina - PI*, com as coordenadas de Teresina.
- Se a cidade não for localizada, o fallback devolve as coordenadas da capital da UF informada, e o metadado `geocoding_*` do roteiro registra `fallback` (função `eh_coordenada_de_fallback`).
- Comprovação: `test_uf_divergente_usa_as_coordenadas_da_cidade_real`, `test_geocoding_escolhe_o_homonimo_da_uf_informada` e `test_geocoding_usa_country_code_e_busca_so_pelo_nome`. Ao vivo (Teste 5): origem **Teresina / RJ** deve gerar *Teresina - PI*.

**No código:** [`services/geocoding.py:98-119`](services/geocoding.py#L98-L119) — consulta com filtro de país (`countryCode=BR`) e leitura do `admin1`

```python
    url = "https://geocoding-api.open-meteo.com/v1/search"
    # A API aceita o nome da cidade sozinho: "cidade + UF" no mesmo texto não devolve resultados.
    # O filtro de país se chama `countryCode` (o parâmetro `country_codes` é ignorado pela API).
    params: dict[str, str | int] = {
        "name": cidade.strip(),
        "count": 10,
        "language": "pt",
        "countryCode": "BR",
    }

    try:
        resposta = client.get(url, params=params, timeout=4.0)
        resposta.raise_for_status()
        resultados = resposta.json().get("results")

        if resultados:
            escolhido = _escolher_resultado(resultados, uf)
            lat: float = escolhido.get("latitude", 0.0)
            lon: float = escolhido.get("longitude", 0.0)
            admin1: str = escolhido.get("admin1", "")
            uf_detectada = obter_sigla_uf(admin1, uf)
            return lat, lon, uf_detectada
```

**No código:** [`services/geocoding.py:76-86`](services/geocoding.py#L76-L86) — escolhe o candidato da UF digitada (ou o primeiro)

```python
def _escolher_resultado(resultados: list[dict[str, Any]], uf: str) -> dict[str, Any]:
    """Escolhe entre os candidatos da API o que pertence à UF informada (via `admin1`).

    Se nenhum candidato estiver na UF digitada, devolve o primeiro (o mais relevante para a API):
    é assim que uma UF errada (ex: Teresina / RJ) acaba corrigida pela UF real da cidade.
    """
    uf_informada = uf.strip().upper()
    for candidato in resultados:
        if obter_sigla_uf(str(candidato.get("admin1", ""))) == uf_informada:
            return candidato
    return resultados[0]
```

**No código:** [`services/geocoding.py:18-29`](services/geocoding.py#L18-L29) — `admin1` (nome do estado) → sigla oficial

```python
    def _normalizar(texto: str) -> str:
        """Remove acentos e converte para minúsculas para comparação robusta."""
        return unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode().lower().strip()

    admin1_normalizado = _normalizar(admin1)

    # Monta mapa invertido: nome normalizado → sigla (ex: "piaui" → "PI")
    mapa_nome_para_sigla = {_normalizar(nome): sigla for sigla, nome in ESTADOS_BRASIL.items()}

    # Tenta encontrar pelo nome normalizado do campo admin1
    if admin1_normalizado in mapa_nome_para_sigla:
        return mapa_nome_para_sigla[admin1_normalizado]
```

**No código:** [`controllers/viagem_controller.py:61-66`](controllers/viagem_controller.py#L61-L66) — o controller aplica a UF corrigida

```python
        # Garante o uso da UF real detectada pelo Geocoding (ex: Teresina / RJ -> corrigido para PI)
        uf_origem_final = uf_origem_det or origem_uf
        uf_destino_final = uf_destino_det or destino_uf

        nome_origem = f"{origem_cidade} - {uf_origem_final}"
        nome_destino = f"{destino_cidade} - {uf_destino_final}"
```


#### 🔐 4. Validação de Token JWT

> **Pergunta do professor:** Explicar como a credencial do Google Identity Services é validada no endpoint oficial `/tokeninfo` conferindo o campo `aud`.

**Resposta (o que falar):**

- **Fluxo completo:** o botão *Sign in with Google* (Google Identity Services) roda no navegador e devolve uma `credential`, que é um **JWT** (`id_token`). O JavaScript coloca essa credencial em um formulário escondido e faz `POST /auth/google/callback`.
- No servidor, `verificar_token_google` chama o endpoint oficial **`https://oauth2.googleapis.com/tokeninfo?id_token=...`**. O Google valida a **assinatura e a expiração** do token e devolve os dados (claims) em JSON; token inválido ou expirado retorna erro HTTP, e `raise_for_status()` transforma isso em `None`.
- Depois conferimos o campo **`aud`** (*audience*): ele precisa ser igual ao nosso `GOOGLE_CLIENT_ID`. Isso garante que o token foi emitido **para o nosso aplicativo**; sem essa checagem, um token válido gerado para *outro* site seria aceito aqui.
- Só então o controller lê `sub` (ID único e estável do usuário), `name`, `email` e `picture` e grava `session["usuario"]`.
- Qualquer falha (timeout, HTTP de erro, `aud` diferente) devolve `None` e o usuário simplesmente volta para a página inicial, sem logar.

**No código:** [`services/google_auth.py:10-31`](services/google_auth.py#L10-L31) — chamada ao `tokeninfo` e conferência do `aud`

```python
def verificar_token_google(client: httpx.Client, token: str) -> dict[str, Any] | None:
    """Valida o token JWT no endpoint oficial 'https://oauth2.googleapis.com/tokeninfo'.

    Verifica se o token foi emitido para o GOOGLE_CLIENT_ID configurado no projeto
    e retorna o payload do usuário (sub, name, email, picture) ou None se for inválido.
    """
    try:
        resposta = client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": token},
            timeout=4.0,
        )
        resposta.raise_for_status()
        payload: dict[str, Any] = resposta.json()

        # Verifica se o token foi emitido para este projeto (campo 'aud' deve bater com o CLIENT_ID)
        if payload.get("aud") != GOOGLE_CLIENT_ID:
            return None

        return payload

    except (httpx.TimeoutException, httpx.HTTPError, Exception):  # noqa: BLE001
```

**No código:** [`controllers/auth_controller.py:14-42`](controllers/auth_controller.py#L14-L42) — rota que recebe a credencial e abre a sessão

```python
@auth_bp.route("/auth/google/callback", methods=["POST"])
def google_callback():
    """Valida o token Google e cria a sessão do usuário."""

    token = request.form.get("credential", "").strip()

    if not token:
        return redirect(url_for("main.index"))

    with httpx.Client() as client:
        dados_usuario = verificar_token_google(client, token)

    if not dados_usuario:
        return redirect(url_for("main.index"))

    user_id = dados_usuario.get("sub")

    if not isinstance(user_id, str) or not user_id:
        return redirect(url_for("main.index"))

    session["usuario"] = {
        "id": user_id,
        "nome": dados_usuario.get("name", "Usuário Google"),
        "email": dados_usuario.get("email", ""),
        "foto": dados_usuario.get("picture", ""),
        "visitante": False,
    }

    return redirect(url_for("main.index"))
```

**No código:** [`templates/index.html:60-62`](templates/index.html#L60-L62) — formulário escondido que envia a `credential`

```html
      <form id="formGoogleLogin" method="POST" action="{{ url_for('auth.google_callback') }}" style="display: none;">
        <input type="hidden" name="credential" id="inputCredential">
      </form>
```

**Se perguntarem:** *“Por que não validar o JWT localmente?”* — Exigiria baixar as chaves públicas do Google (JWKS) e verificar a assinatura. Delegar ao `tokeninfo` é mais simples; o custo é uma chamada de rede extra por login.


#### 🚨 5. Tratamento Global de Erros e endpoint `GET /viagens/json`

> **Pergunta do professor:** Explicar os manipuladores `@app.errorhandler(404)` e `@app.errorhandler(405)` e o endpoint REST `GET /viagens/json`.

**Resposta (o que falar):**

- **404** (rota inexistente) e **405** (método não permitido, por exemplo digitar `/viagens/criar` na barra de endereços, que só aceita POST) são interceptados de forma **global** e respondem com um redirecionamento (302) para a página inicial, em vez de mostrar a página de erro.
- Na arquitetura MVC os handlers ficam em um Blueprint e usam **`@api_bp.app_errorhandler`**, que é o equivalente de `@app.errorhandler`: registra o tratamento para o **aplicativo inteiro**, e não só para as rotas daquele Blueprint. (`@bp.errorhandler` valeria apenas para o Blueprint.)
- **`GET /viagens/json`** devolve a base consolidada como JSON: `jsonify(...)` produz a resposta com `Content-Type: application/json`. A rota tem também os aliases `/api/viagens/json` e `/api/viagens`.
- A resposta é montada por `montar_payload_consolidado`: lê o arquivo `viagens.json` e **mescla os roteiros do visitante** (que só existem em memória) quando a sessão é de visitante, além de recalcular os totais.
- Comprovação: o teste `test_rotas_invalidas_redirecionam_para_home` chama uma rota inexistente, `GET /viagens/criar` e `GET /viagens/deletar/abc`; todos respondem 302 para `/`.

**No código:** [`controllers/api_controller.py:10-34`](controllers/api_controller.py#L10-L34) — endpoint REST e handlers 404, 405 e 500

```python
@api_bp.route("/viagens/json", methods=["GET"])
@api_bp.route("/api/viagens/json", methods=["GET"])
@api_bp.route("/api/viagens", methods=["GET"])
def ver_viagens_json():
    """Retorna a base consolidada de static/data/viagens.json com suporte dinâmico a visitantes."""
    return jsonify(montar_payload_consolidado(session.get("usuario")))


@api_bp.app_errorhandler(405)
def metodo_nao_permitido(error):
    """Fallback para acessos GET em rotas POST (ex: digitar /viagens/criar na barra de endereços)."""
    return redirect(url_for("main.index"))


@api_bp.app_errorhandler(404)
def pagina_nao_encontrada(error):
    """Fallback para rotas inexistentes redirecionando suavemente para a página principal."""
    return redirect(url_for("main.index"))


@api_bp.app_errorhandler(500)
def erro_interno(error):
    """Redireciona erros internos do servidor para a página inicial."""

    return redirect(url_for("main.index"))
```

**No código:** [`models/viagem_repository.py:280-309`](models/viagem_repository.py#L280-L309) — quem monta o JSON consolidado (mescla os roteiros do visitante em memória)

```python
def montar_payload_consolidado(usuario_sessao: Any) -> dict[str, Any]:
    """Base consolidada do JSON, mesclada com as viagens em memória do visitante da sessão (se houver)."""
    with lock_arquivo_json:
        dados = carregar_dados_viagens_json() or criar_estrutura_padrao_viagens()

        # Mescla as viagens do visitante em memória (se houver sessão ativa)
        visitante = obter_roteiros_visitante(usuario_sessao)
        if visitante:
            user_id, roteiros_mem = visitante
            perfil = dict(usuario_sessao)
            if "picture" in perfil and "foto" not in perfil:
                perfil["foto"] = perfil["picture"]

            agora_iso = datetime.now(timezone.utc).isoformat()
            dados.setdefault("usuarios", {})[user_id] = {
                "perfil": perfil,
                "metadados": {
                    "total_roteiros": len(roteiros_mem),
                    "criado_em": roteiros_mem[0].get("criado_em", agora_iso) if roteiros_mem else agora_iso,
                    "atualizado_em": roteiros_mem[-1].get("criado_em", agora_iso) if roteiros_mem else agora_iso,
                },
                "roteiros": list(roteiros_mem),
            }

        usuarios = dados.get("usuarios", {})
        if isinstance(usuarios, dict):
            dados["total_usuarios"] = len(usuarios)
            dados["total_roteiros"] = _contar_roteiros(usuarios)

        return dados
```


---

### 👤 Douglas Leone — Telemetria, Rotas e Inteligência Artificial

#### 📦 1. Tipagem Estática & Qualidade

> **Pergunta do professor:** Explicar as assinaturas modernas em Python 3.10+ (`tuple[float, float, str]`, `dict[str, Any] | None`) e a validação com `ruff check .` e `mypy .`.

**Resposta (o que falar):**

- Uso a sintaxe moderna do Python: `tuple[...]`, `dict[...]` e `list[...]` são escritos direto, **sem importar `Tuple` e `Dict` do `typing`** (PEP 585, Python 3.9). O operador **`|`** substitui `Optional` e `Union` (PEP 604, Python 3.10).
- `tuple[float, float, str]` é uma tupla de **tamanho fixo, com um tipo por posição**: latitude, longitude e UF. Quem chama desempacota direto: `lat, lon, uf = buscar_coordenadas(...)`.
- `dict[str, Any] | None` significa “um dicionário **ou** `None`”: o token válido devolve o payload do Google e o inválido devolve `None`. Equivale a `Optional[Dict[str, Any]]`.
- `-> dict[str, str]` (clima e rota): todos os valores são strings já formatadas, inclusive o fallback `"N/D"`. **Sucesso e falha têm o mesmo tipo**, e o template exibe direto.
- O Python **ignora as anotações em tempo de execução**. Quem as verifica é o **mypy**, um verificador *estático*: analisa o código sem executá-lo e acusa, por exemplo, um `str` passado onde se espera `float`.
- O **ruff** é um linter (escrito em Rust, muito rápido): aponta import sem uso, variável sem uso, `except` genérico e problemas de estilo.
- Resultado no projeto: `ruff check .` → `All checks passed!` e `mypy .` → `Success: no issues found in 20 source files`.

**No código:** [`services/geocoding.py:89-91`](services/geocoding.py#L89-L91) — `tuple[float, float, str]`

```python
def buscar_coordenadas(
    client: httpx.Client, cidade: str, uf: str = ""
) -> tuple[float, float, str]:
```

**No código:** [`services/google_auth.py:10`](services/google_auth.py#L10) — `dict[str, Any] | None`

```python
def verificar_token_google(client: httpx.Client, token: str) -> dict[str, Any] | None:
```

**No código:** [`services/clima.py:6`](services/clima.py#L6) — `dict[str, str]`

```python
def obter_clima(client: httpx.Client, lat: float, lon: float) -> dict[str, str]:
```

**No código:** [`services/gemini.py:99`](services/gemini.py#L99) — `tuple[str, dict[str, Any]]`

```python
def obter_guia_destino_com_diagnostico(destino: str) -> tuple[str, dict[str, Any]]:
```

**No código:** [`services/clima.py:48-49`](services/clima.py#L48-L49) — o `# noqa: BLE001` silencia de propósito a regra contra `except Exception`

```python
    except (httpx.TimeoutException, httpx.HTTPError, Exception):  # noqa: BLE001
        return fallback
```

**Se perguntarem:**
- *“Por que `# noqa: BLE001`?”* — BLE001 é a regra do ruff que proíbe `except Exception` genérico. Foi silenciada de propósito: o contrato dessas funções é **nunca derrubar a requisição** e sempre devolver um fallback.
- *“`except (TimeoutException, HTTPError, Exception)` não é redundante?”* — É: `Exception` já cobre as outras duas. As específicas ficam ali como documentação dos erros esperados.
- *“O Python valida os tipos ao rodar?”* — Não. As anotações não mudam a execução; quem verifica é o mypy, antes de rodar.

Para rodar ao vivo:

```bash
ruff check .
mypy .
```


#### 🚗 2. Telemetria de Clima e Rotas

> **Pergunta do professor:** Explicar o consumo das APIs Open-Meteo Weather e OSRM, a conversão de metros para km (`round(m/1000, 1)`) e de segundos para horas/minutos.

**Resposta (o que falar):**

- **Open-Meteo Forecast** (`/v1/forecast`): recebe latitude, longitude e `current=temperature_2m,relative_humidity_2m,wind_speed_10m`. É gratuita, **sem chave**, e as unidades padrão já são °C, % e km/h. Timeout de 4 s.
- Se as coordenadas forem `(0.0, 0.0)`, o geocoding falhou: a função nem chama a API e devolve `N/D`. A leitura usa `.get("current", {})` e, se algum campo vier `None`, devolve o fallback.
- **OSRM** (`/route/v1/driving/...?overview=false`): calcula a rota de carro. ⚠️ **A longitude vem primeiro** (`{lon},{lat};{lon},{lat}`), convenção GeoJSON, ao contrário do costume “lat, lon”. `overview=false` dispensa o desenho da rota e deixa a resposta menor.
- **Destino sem estrada (ilha):** o OSRM “puxa” (*snap*) o ponto para a estrada mais próxima. Se essa distância passar de **10 km** (`waypoints[1].distance > 10000`), a função responde “Sem rota direta / Considere voos ou barcos”. É o caso de Fernando de Noronha.
- **Metros → km:** `round(metros / 1000, 1)`. Exemplo: `1674512 m → 1674.5 km`.
- **Segundos → horas e minutos:** `horas = segundos // 3600` (divisão inteira) e `minutos = round((segundos % 3600) / 60)` (`%` é o resto da divisão). Exemplo: `9000 s → 2 h` e resto `1800 s = 30 min` → `2h 30min`.
- **Caso especial:** `3590 s` dá 0 h e `round(59.8) = 60` minutos, então o `if minutos == 60` converte para `1h 00min`. E `:02d` completa com zero (`1h 05min`).

**No código:** [`services/clima.py:18-46`](services/clima.py#L18-L46) — Open-Meteo Weather

```python
    # Validação rápida de coordenadas zeradas
    if lat == 0.0 and lon == 0.0:
        return fallback

    url = "https://api.open-meteo.com/v1/forecast"
    params: dict[str, str | float] = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
    }

    try:
        resposta = client.get(url, params=params, timeout=4.0)
        resposta.raise_for_status()
        dados = resposta.json()
        current = dados.get("current", {})

        temperatura = current.get("temperature_2m")
        umidade = current.get("relative_humidity_2m")
        vento = current.get("wind_speed_10m")

        if temperatura is None or umidade is None or vento is None:
            return fallback

        return {
            "temperatura": f"{temperatura} °C",
            "umidade": f"{umidade}%",
            "vento": f"{vento} km/h",
        }
```

**No código:** [`services/rotas.py:24-26`](services/rotas.py#L24-L26) — OSRM: longitude primeiro

```python
    # OSRM espera coordenadas no formato: {longitude},{latitude};{longitude},{latitude}
    url = f"https://router.project-osrm.org/route/v1/driving/{lon_o},{lat_o};{lon_d},{lat_d}"
    params: dict[str, str] = {"overview": "false"}
```

**No código:** [`services/rotas.py:41-48`](services/rotas.py#L41-L48) — destino sem estrada (ilha)

```python
        # Verificação defensiva de snap (ilhas/destinos sem malha rodoviária conectada).
        # O OSRM pode 'encaixar' destinos insulares na costa mais próxima. Se o ponto de destino
        # estiver a mais de 10 km (10.000m) da estrada navegável mais próxima, consideramos sem rota direta.
        waypoints = dados.get("waypoints", [])
        if len(waypoints) >= 2:
            dist_snap_destino = waypoints[1].get("distance", 0.0)
            if dist_snap_destino > 10000.0:
                return fallback_sem_rota
```

**No código:** [`services/rotas.py:50-69`](services/rotas.py#L50-L69) — conversões de unidade

```python
        rota = routes[0]
        distancia_metros: float = rota.get("distance", 0.0)
        duracao_segundos: float = rota.get("duration", 0.0)

        # Conversão de unidades: metros para quilômetros com 1 casa decimal
        distancia_km = round(distancia_metros / 1000.0, 1)

        # Conversão de duração: segundos para horas e minutos inteiros
        horas = int(duracao_segundos // 3600)
        minutos = round((duracao_segundos % 3600) / 60.0)

        # Ajuste caso o arredondamento dos minutos resulte em 60
        if minutos == 60:
            horas += 1
            minutos = 0

        if horas > 0:
            tempo_formatado = f"{horas}h {minutos:02d}min de carro"
        else:
            tempo_formatado = f"{minutos}min de carro"
```

**Se perguntarem:** *“Por que o `int()` nas horas?”* — Porque `//` aplicado a `float` devolve `float` (`2.0`); o `int()` deixa `2`.

Teste ao vivo (Teste 5 do professor): destino **Fernando de Noronha / PE** deve mostrar “Sem rota direta” e “Considere voos ou barcos”. Também comprovado em `python testar_douglas.py`.


#### 🤖 3. Engenharia de Prompt

> **Pergunta do professor:** Explicar as restrições aplicadas no prompt para forçar respostas em texto puro com emojis, sem asteriscos ou marcações Markdown.

**Resposta (o que falar):**

- O front exibe o guia **cru**, dentro de um `<div class="guia-texto">` com `white-space: pre-line`, e **não interpreta Markdown**. Se a IA mandasse `**negrito**`, os asteriscos apareceriam na tela. Por isso o prompt força texto puro.
- **Persona:** “renomado consultor turístico especialista no Brasil”.
- **Estrutura obrigatória:** 4 títulos exatos com emoji (🏛️ 🗺️ 🍲 💡) e bullets `•`. São os mesmos títulos do guia de contingência, então a tela fica igual com ou sem IA.
- **Tamanho controlado:** 1 a 2 frases por item e quantidades fixas (3 atrações, manhã/tarde/noite, 3 pratos, 2 dicas).
- **Restrições negativas explícitas:** o bloco “REGRAS ESTREITAS DE FORMATO” cita cada símbolo pelo nome (`*`, `**`, `#`, `_` e crases) e proíbe saudação e despedida.
- **Âncora de início:** “Comece imediatamente pelo título 🏛️ PONTOS TURÍSTICOS PRINCIPAIS”.
- **Configuração para caber no timeout:** `thinking_budget=0` (sem raciocínio interno, mais rápido), `max_output_tokens=650` e `temperature=0.7`.
- O prompt *previne*, mas o modelo nem sempre obedece; por isso existe o regex do próximo ponto. É defesa em camadas.

**No código:** [`services/gemini.py:27-47`](services/gemini.py#L27-L47) — o prompt, com a estrutura e as regras de formato

```python
    prompt = (
        f"Você é um renomado consultor turístico especialista no Brasil. "
        f"Crie um roteiro e guia turístico aprofundado, autêntico, dinâmico e altamente específico para a cidade de {destino}. "
        "Seja envolvente, objetivo e direto ao ponto (1 a 2 frases por tópico).\n\n"
        "ESTRUTURA OBRIGATÓRIA (utilize exatamente estes títulos com emojis):\n"
        "🏛️ PONTOS TURÍSTICOS PRINCIPAIS\n"
        "• Cite 3 atrações imperdíveis com nomes reais, pontos de referência exatos e experiências marcantes "
        "(mirantes, cachoeiras, igrejas históricas, reservas naturais ou sítios da região) em até 2 frases objetivas por bullet •.\n\n"
        "🗺️ ROTEIRO RECOMENDADO (PASSO A PASSO)\n"
        "• Manhã: Experiência matinal imperdível em 1 ou 2 frases (ex: nascer do sol, mirante matinal, caminhada ou centro histórico).\n"
        "• Tarde: Passeio vespertino em 1 ou 2 frases (ex: trilha, cachoeira com banho refrescante, alambique/engenho tradicional ou feira).\n"
        "• Noite: Vivência noturna autêntica em 1 ou 2 frases (ex: praça principal movimentada, polo gastronômico ou cafés aconchegantes).\n\n"
        "🍲 CULINÁRIA LOCAL & GASTRONOMIA\n"
        "• Descreva 3 pratos típicos genuínos, quitutes, bebidas ou sobremesas tradicionais da culinária da região com nomes reais populares em 1 ou 2 frases cada.\n\n"
        "💡 DICA DE OURO DO VIAJANTE\n"
        "• Forneça 2 recomendações práticas de alto valor sobre melhor horário para fotos/mirantes, agasalhos para o clima da serra ou feiras locais (1 ou 2 frases cada).\n\n"
        "REGRAS ESTREITAS DE FORMATO:\n"
        "- Responda EXCLUSIVAMENTE em texto puro com emojis legíveis.\n"
        "- NÃO use nenhuma marcação Markdown (NÃO use asteriscos *, nem **, nem hashtags #, nem sublinhados _, nem crases `).\n"
        "- NÃO inclua saudações iniciais (ex: 'Olá', 'Com certeza!') nem despedidas (ex: 'Boa viagem!'). Comece imediatamente pelo título '🏛️ PONTOS TURÍSTICOS PRINCIPAIS'."
    )
```

**No código:** [`services/gemini.py:49-54`](services/gemini.py#L49-L54) — configuração da chamada

```python
    # Configuração com thinking_budget=0 e limite de tokens para latência mínima (<3.5s), garantindo resposta antes do timeout
    config_rapida = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        temperature=0.7,
        max_output_tokens=650,
    )
```

**No código:** [`templates/index.html:159`](templates/index.html#L159) — o guia é exibido como texto puro

```html
              <div class="guia-texto">{{ v.dicas_destino }}</div>
```

**Se perguntarem:** *“Qual modelo responde?”* — A lista tenta `gemini-2.5-flash` primeiro (~2,5 s, cabe no limite de 6 s), depois `gemini-3.6-flash` e por fim `gemini-2.5-flash-lite`. O diagnóstico registra o modelo que **realmente** respondeu.


#### 🛡️ 4. Sanitização Regex & Fallback da IA

> **Pergunta do professor:** Explicar a função `limpar_formato_texto()`, o isolamento em `ThreadPoolExecutor(timeout=6.0s)` e o disparo do guia de contingência.

**Resposta (o que falar):**

- São **três camadas**: o prompt *previne*, o regex *corrige* o que a IA desobedecer e o fallback *substitui* o texto quando a IA falha.
- `limpar_formato_texto()` aplica, em ordem: remove crases; converte listas `*` e `-` do começo da linha em `•` (`(?m)` faz o `^` valer para **cada linha**); remove títulos `#`; tira negrito com `\*\*([^*]+)\*\*` → `\1` (o grupo `( )` captura o texto e `\1` o devolve sem os asteriscos); tira itálico e asteriscos soltos; remove a **saudação da primeira linha** e a **despedida da última**; e junta linhas em branco repetidas.
- **A ordem importa:** a lista é convertida antes do negrito. Senão, em `* **Pelourinho**`, o `*` do marcador seria confundido com início de itálico.
- **ThreadPoolExecutor:** a chamada ao SDK do Gemini é **síncrona e bloqueante** (e pode tentar até 3 modelos em sequência). Rodando numa thread separada dá para usar `future.result(timeout=6.0)`, que lança `TimeoutError` quando o tempo estoura.
- **Por que o executor não usa `with`:** o `__exit__` chama `shutdown(wait=True)` e esperaria a thread terminar, e aí o timeout não adiantaria de nada. Com `shutdown(wait=False, cancel_futures=True)` no `finally`, a resposta sai em 6 s cravados e a thread termina sozinha em segundo plano. Testado: um Gemini simulado de 10 s retorna em **6,0 s**.
- **Três gatilhos do fallback:** (1) chave vazia, sem nem chamar a API; (2) timeout de 6 s; (3) qualquer exceção, como chave inválida (400) ou falta de cota (429).
- **Guia de contingência:** é determinístico. Tira os acentos do nome, procura a cidade na base curada `_GUIAS_CURADOS` (Fortaleza, Teresina, Brasília, Noronha, Salvador, Rio, São Paulo, Recife, Tianguá) e, se não achar, gera um guia genérico com os mesmos 4 títulos. O diagnóstico grava `fallback_utilizado: true` e o motivo, e a tela mostra o badge **“Modo Contingência”**.

**No código:** [`services/sanitizacao.py:12-41`](services/sanitizacao.py#L12-L41) — `limpar_formato_texto()`: crases, listas, títulos, negrito, itálico, saudação e despedida

````python
    texto_limpo = texto.replace("```", "").replace("`", "")

    # Converte marcadores de lista markdown (* ou -) em bullets amigáveis (•)
    texto_limpo = re.sub(r"(?m)^[\*\-]\s+", "• ", texto_limpo)

    # Remove marcadores de cabeçalho markdown (# Título, ## Subtítulo)
    texto_limpo = re.sub(r"(?m)^#+\s*", "", texto_limpo)

    # Remove marcações de negrito e itálico (**texto**, *texto*, __texto__)
    texto_limpo = re.sub(r"\*\*([^*]+)\*\*", r"\1", texto_limpo)
    texto_limpo = re.sub(r"\*([^*]+)\*", r"\1", texto_limpo)
    texto_limpo = texto_limpo.replace("**", "").replace("*", "")
    texto_limpo = re.sub(r"__([^_]+)__", r"\1", texto_limpo)

    # Remove saudações conversacionais típicas de LLM na primeira linha
    texto_limpo = re.sub(
        r"(?i)^(olá|ola|com certeza|claro|aqui está|aqui esta|segue|preparado|bem-vindo)[^\n]*\n+",
        "",
        texto_limpo.strip(),
    )

    # Remove despedidas e mensagens de encerramento no final
    texto_limpo = re.sub(
        r"(?i)\n+(espero que aproveite|boa viagem|aproveite sua viagem|espero ter ajudado|qualquer dúvida)[^\n]*$",
        "",
        texto_limpo.strip(),
    )

    # Normaliza múltiplas linhas em branco para espaçamento uniforme
    texto_limpo = re.sub(r"\n{3,}", "\n\n", texto_limpo)
````

**No código:** [`services/gemini.py:106-132`](services/gemini.py#L106-L132) — gatilho 1 (chave vazia) e o isolamento em ThreadPoolExecutor com timeout de 6 s

```python
    chave_atual = os.getenv("GEMINI_API_KEY", GEMINI_KEY)
    # Validação rápida de chave vazia
    if not chave_atual or chave_atual.strip() == "" or chave_atual == "SUA_CHAVE_AQUI":
        guia_contingencia = gerar_guia_contingencia(destino)
        diagnostico: dict[str, Any] = {
            "status": "fallback",
            "modelo": MODELO_OFICIAL,
            "fallback_utilizado": True,
            "motivo": "Chave GEMINI_API_KEY não configurada",
        }
        return guia_contingencia, diagnostico

    # Isolamento com ThreadPoolExecutor para garantir timeout estrito de 6.0s.
    # O executor não usa 'with': o __exit__ chamaria shutdown(wait=True) e a requisição
    # ficaria presa esperando a thread do Gemini terminar, mesmo após o timeout.
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(_executar_chamada_gemini, destino)
        texto_bruto, modelo_utilizado = future.result(timeout=6.0)

        texto_formatado = limpar_formato_texto(texto_bruto)
        diagnostico = {
            "status": "sucesso",
            "modelo": modelo_utilizado,
            "fallback_utilizado": False,
        }
        return texto_formatado, diagnostico
```

**No código:** [`services/gemini.py:134-156`](services/gemini.py#L134-L156) — gatilhos 2 e 3, e o `shutdown(wait=False)` no `finally`

```python
    except concurrent.futures.TimeoutError:
        guia_contingencia = gerar_guia_contingencia(destino)
        diagnostico = {
            "status": "fallback",
            "modelo": MODELO_OFICIAL,
            "fallback_utilizado": True,
            "motivo": "Timeout na chamada à API Gemini (limite de 6.0s excedido)",
        }
        return guia_contingencia, diagnostico

    except Exception as erro:  # noqa: BLE001
        guia_contingencia = gerar_guia_contingencia(destino)
        diagnostico = {
            "status": "fallback",
            "modelo": MODELO_OFICIAL,
            "fallback_utilizado": True,
            "motivo": f"Falha na API Gemini: {erro}",
        }
        return guia_contingencia, diagnostico

    finally:
        # Libera a requisição imediatamente; a thread em andamento termina sozinha em segundo plano
        executor.shutdown(wait=False, cancel_futures=True)
```

**No código:** [`services/contingencia.py:143-168`](services/contingencia.py#L143-L168) — guia de contingência determinístico (cidades curadas; as demais recebem um guia genérico logo abaixo)

```python
def gerar_guia_contingencia(destino: str) -> str:
    """Gera roteiro estruturado determinístico em texto puro com emojis em caso de falha da IA."""
    nome_destino = destino.strip() or "Destino Selecionado"
    nome_sem_uf = re.sub(r"\s*-\s*[A-Z]{2}$", "", nome_destino).strip()
    nfkd = unicodedata.normalize("NFKD", nome_sem_uf)
    nome_chave = "".join(c for c in nfkd if not unicodedata.combining(c)).lower()

    # Se o destino for uma das cidades mapeadas, entrega curadoria refinada
    for chave, dados in _GUIAS_CURADOS.items():
        if chave in nome_chave or nome_chave in chave:
            pontos_txt = "\n".join(f"• {p}" for p in dados["pontos"])
            roteiro_bloco = ""
            if "roteiro" in dados:
                roteiro_txt = "\n".join(f"• {r}" for r in dados["roteiro"])
                roteiro_bloco = f"\n🗺️ ROTEIRO RECOMENDADO (PASSO A PASSO)\n{roteiro_txt}\n"
            culinaria_txt = "\n".join(f"• {c}" for c in dados["culinaria"])
            dica_txt = f"• {dados['dica']}"
            return (
                f"🏛️ PONTOS TURÍSTICOS PRINCIPAIS\n"
                f"{pontos_txt}\n"
                f"{roteiro_bloco}\n"
                f"🍲 CULINÁRIA LOCAL & GASTRONOMIA\n"
                f"{culinaria_txt}\n\n"
                f"💡 DICA DE OURO DO VIAJANTE\n"
                f"{dica_txt}"
            )
```

**Teste 2 do professor** (`GEMINI_API_KEY="CHAVE_INVALIDA"`): a API responde 400, a exceção é capturada e o card exibe o roteiro de contingência em texto puro, **sem erro 500**.

```powershell
$env:GEMINI_API_KEY="CHAVE_INVALIDA"
python app.py
```

A variável de ambiente tem prioridade sobre o `.env`.


---

### 👤 Mikaelle Barroso — Backend Gateway, Sessões, Idempotência e Persistência JSON

#### 🔄 1. Ciclo de Vida HTTP (POST vs GET)

> **Pergunta do professor:** Explicar a diferença semântica entre a rota `/` (GET idempotente) e a rota `/viagens/criar` (POST não-idempotente).

**Resposta (o que falar):**

- **Idempotente** significa que repetir a mesma requisição N vezes tem o mesmo efeito de fazê-la uma vez.
- **`GET /`** só **lê**: busca os roteiros do usuário e renderiza a página, sem alterar nada no servidor. É seguro e idempotente, então pode ser repetido, guardado em cache e favoritado.
- **`POST /viagens/criar`** **altera o estado**: cada execução cria um roteiro novo (e consome APIs externas). Repetir o POST gera duplicatas, então **não é idempotente**.
- Por isso a rota declara `methods=["POST"]`: os dados vão no **corpo** da requisição (não na URL), e um `GET /viagens/criar` cai no erro 405, tratado com redirecionamento para `/`. A exclusão (`/viagens/deletar/<id>`) também é só POST, porque **um link GET não deve apagar dados**.
- Como o POST não é idempotente, o projeto precisa de duas proteções: o **PRG** (ponto 2) e o **bloqueio de cliques duplos** (ponto 3).

**No código:** [`controllers/main_controller.py:11-31`](controllers/main_controller.py#L11-L31) — GET `/`: apenas lê e renderiza

```python
@main_bp.route("/")
def index():
    """Exibe a página principal com sessão e roteiros do usuário."""

    usuario = session.get("usuario")

    viagens = []

    if isinstance(usuario, dict):
        user_id = usuario.get("id")

        if isinstance(user_id, str):
            viagens = obter_viagens_usuario(user_id)

    return render_template(
        "index.html",
        usuario=usuario,
        viagens=viagens,
        ufs=ESTADOS_BRASIL.keys(),
        client_id=GOOGLE_CLIENT_ID,
    )
```

**No código:** [`controllers/viagem_controller.py:133-135`](controllers/viagem_controller.py#L133-L135) — POST `/viagens/criar`: só aceita POST

```python
@viagens_bp.route("/viagens/criar", methods=["POST"])
def criar_viagem():
    """Processa o formulário de criação e orquestra os serviços externos."""
```

**No código:** [`controllers/viagem_controller.py:203-205`](controllers/viagem_controller.py#L203-L205) — excluir também é só POST

```python
@viagens_bp.route("/viagens/deletar/<string:viagem_id>", methods=["POST"])
def deletar_viagem(viagem_id: str):
    """Exclui um roteiro da lista do usuário."""
```


#### 🛡️ 2. Padrão Post/Redirect/Get (PRG)

> **Pergunta do professor:** Explicar por que a rota de criação responde com HTTP 302 Found redirecionando para a home (evitando reenvio acidental com F5).

**Resposta (o que falar):**

- Se o POST respondesse renderizando a página diretamente, o navegador ficaria **na URL do POST**. Ao apertar **F5**, ele perguntaria “reenviar o formulário?” e, se o usuário confirmasse, **repetiria o POST e criaria o roteiro duplicado**.
- No PRG, o servidor processa o POST e responde **`302 Found`** com o cabeçalho `Location: /`. O navegador então faz um **GET `/`** automaticamente. A URL final é a da home, e o **F5 só repete o GET** (seguro).
- O `redirect(url_for("main.index"))` do Flask usa 302 por padrão. `url_for` gera a URL a partir do **nome do endpoint**, em vez de uma string fixa.
- O padrão vale para todos os POSTs: criar (inclusive quando a validação falha), excluir e os logins.
- Comprovação: em `test_criar_viagem_persiste_schema_e_aparece_na_home` o POST responde 302 e a lista aparece no GET seguinte.

**No código:** [`controllers/viagem_controller.py:188-200`](controllers/viagem_controller.py#L188-L200) — ao final do POST, o redirecionamento 302 para a home

```python
    try:
        viagem = _gerar_roteiro(origem_cidade, origem_uf, destino_cidade, destino_uf)

        adicionar_viagem_usuario(
            usuario["id"],
            viagem,
            perfil_usuario=usuario,
        )
    finally:
        with lock_requisicoes:
            requisicoes_ativas.discard(chave_requisicao)

    return redirect(url_for("main.index"))
```


#### 🔒 3. Idempotência & Bloqueio de Concorrência

> **Pergunta do professor:** Explicar como o frontend (desabilitação do botão com spinner) e o backend (`threading.Lock` e controle de requisições recentes) evitam cliques duplos.

**Resposta (o que falar):**

- São **duas camadas**, e a segunda é a que realmente garante, porque o navegador pode ser burlado (F12, `curl`, dois cliques rápidos).
- **Frontend (`app.js`):** ao enviar o formulário, a flag `submetido` vira `true`, o botão é **desabilitado** (`btn.disabled = true`) e o texto muda para “⏳ Consultando APIs e Gemini AI...”. Um segundo envio é cancelado com `e.preventDefault()`. Um timer de segurança libera o botão após 12 s, caso a rede falhe.
- **Backend:** monta uma **chave** que identifica a operação (`usuário|origem|uf|destino|uf`) e usa dois controles: `requisicoes_ativas` (conjunto das operações **em andamento**) e `requisicoes_recentes` (horário da última execução, com **janela de 10 s**). Se a chave já está ativa ou foi executada há menos de 10 s, a requisição é descartada com redirecionamento.
- O **`threading.Lock`** (`lock_requisicoes`) torna atômico o “verificar e registrar”. Sem ele, duas requisições simultâneas poderiam checar ao mesmo tempo, ambas concluírem que não há duplicata e passarem as duas. O `finally` sempre libera a chave, mesmo se der erro.
- Comprovação: o teste `test_cliques_duplos_criam_um_unico_roteiro` dispara **5 POSTs simultâneos** e verifica que só **1** roteiro é criado.

**No código:** [`static/js/app.js:63-88`](static/js/app.js#L63-L88) — frontend: botão desabilitado com spinner e bloqueio do segundo envio

```javascript
    form.addEventListener("submit", function (e) {
      // Se os campos obrigatórios não foram preenchidos, não trava o botão
      if (!form.checkValidity()) {
        return;
      }

      if (submetido) {
        // Bloqueia cliques duplos rápidos
        e.preventDefault();
        return false;
      }

      submetido = true;
      const btn = document.getElementById("btnGerarGuia");
      if (btn) {
        btn.disabled = true;
        btn.innerText = "⏳ Consultando APIs e Gemini AI...";
        btn.style.opacity = "0.75";
        btn.style.cursor = "not-allowed";
      }

      // Timer de segurança: se a rede ou servidor demorar mais de 12 segundos, libera o botão
      timerSeguranca = setTimeout(function () {
        resetarEstadoBotao();
      }, 12000);
    });
```

**No código:** [`controllers/viagem_controller.py:25-28`](controllers/viagem_controller.py#L25-L28) — estado compartilhado e lock

```python
# Controle de concorrência e idempotência contra cliques duplicados
requisicoes_ativas: set[str] = set()
requisicoes_recentes: dict[str, float] = {}
lock_requisicoes = threading.Lock()
```

**No código:** [`controllers/viagem_controller.py:166-198`](controllers/viagem_controller.py#L166-L198) — backend: chave, verificação atômica com lock e liberação no `finally`

```python
    chave_requisicao = (
        f"{usuario['id']}|"
        f"{origem_cidade.lower()}|"
        f"{origem_uf}|"
        f"{destino_cidade.lower()}|"
        f"{destino_uf}"
    )

    agora = time.time()

    with lock_requisicoes:
        if chave_requisicao in requisicoes_ativas:
            return redirect(url_for("main.index"))

        ultima_requisicao = requisicoes_recentes.get(chave_requisicao)

        if ultima_requisicao is not None and agora - ultima_requisicao < 10:
            return redirect(url_for("main.index"))

        requisicoes_ativas.add(chave_requisicao)
        requisicoes_recentes[chave_requisicao] = agora

    try:
        viagem = _gerar_roteiro(origem_cidade, origem_uf, destino_cidade, destino_uf)

        adicionar_viagem_usuario(
            usuario["id"],
            viagem,
            perfil_usuario=usuario,
        )
    finally:
        with lock_requisicoes:
            requisicoes_ativas.discard(chave_requisicao)
```


#### 👤 4. Segurança de Sessão

> **Pergunta do professor:** Explicar como o dicionário `session["usuario"]` persiste o usuário autenticado por meio de cookies criptografados e como funciona o Modo Visitante.

**Resposta (o que falar):**

- O servidor **não guarda a sessão em memória**: ela fica em um **cookie** no navegador. O Flask serializa o dicionário `session` e o **assina** com a `SECRET_KEY` (HMAC, via *itsdangerous*).
- A cada requisição o navegador devolve o cookie, o Flask **confere a assinatura** e reconstrói o `session`. Assim `session.get("usuario")` identifica quem está logado. Se o cookie for adulterado, a assinatura não bate e a sessão é descartada.
- ⚠️ **Precisão importante:** o cookie padrão do Flask é **assinado, não criptografado**. O conteúdo é codificado em base64 e **pode ser lido** por quem inspecionar o cookie; o que a assinatura garante é que ninguém consegue **alterá-lo** sem a chave. Por isso não se guardam segredos na sessão, apenas `id`, `nome`, `email`, `foto` e `visitante`.
- A `SECRET_KEY` vem da variável de ambiente e existe um valor padrão só para desenvolvimento; **em produção deve ser definida no `.env`**, porque quem a conhece consegue forjar cookies.
- **Modo Visitante (`/auth/demo`):** gera um id `visitante-<uuid>`, grava `session["usuario"]` com `visitante: True` e reserva uma lista **em memória** (`viagens_visitante_memoria`). Os roteiros do visitante **nunca vão para o `viagens.json`**: `eh_usuario_visitante` decide pelo prefixo do id e pelo flag, e não depende da memória, então mesmo após reiniciar o servidor o visitante não cai no arquivo. O logout limpa a sessão e apaga a memória do visitante.
- Comprovação: `test_visitante_fica_so_em_memoria` e `test_visitante_com_memoria_zerada_nao_grava_no_json`.

**No código:** [`controllers/auth_controller.py:34-40`](controllers/auth_controller.py#L34-L40) — login Google grava o usuário na sessão

```python
    session["usuario"] = {
        "id": user_id,
        "nome": dados_usuario.get("name", "Usuário Google"),
        "email": dados_usuario.get("email", ""),
        "foto": dados_usuario.get("picture", ""),
        "visitante": False,
    }
```

**No código:** [`controllers/auth_controller.py:45-66`](controllers/auth_controller.py#L45-L66) — Modo Visitante

```python
@auth_bp.route("/auth/demo", methods=["GET", "POST"])
def login_demo():
    """Cria uma sessão temporária para o visitante."""

    user_id = f"visitante-{uuid.uuid4().hex}"

    session.clear()

    avatar = url_for("static", filename="img/visitante.svg")

    session["usuario"] = {
        "id": user_id,
        "nome": "Viajante Convidado",
        "email": "",
        "foto": avatar,
        "picture": avatar,
        "visitante": True,
    }

    iniciar_visitante(user_id)

    return redirect(url_for("main.index"))
```

**No código:** [`app.py:22`](app.py#L22) — chave que assina o cookie

```python
    aplicacao.secret_key = os.getenv("SECRET_KEY", "guia-turista-secret-key-2026-python")
```

**No código:** [`models/viagem_repository.py:14-15`](models/viagem_repository.py#L14-L15) — roteiros de visitantes só em memória

```python
# Armazenamento volátil de roteiros em memória para sessões de visitantes
viagens_visitante_memoria: dict[str, list[dict[str, Any]]] = {}
```

**No código:** [`models/viagem_repository.py:18-25`](models/viagem_repository.py#L18-L25) — decide se é visitante, sem depender da memória

```python
def eh_usuario_visitante(
    user_id: str,
    perfil_usuario: dict[str, Any] | None = None,
) -> bool:
    """Verifica de forma definitiva se o usuário é visitante (mesmo se a memória zerar após reinício)."""
    if isinstance(user_id, str) and user_id.startswith(("visitante", "guest")):
        return True
    return bool(perfil_usuario and isinstance(perfil_usuario, dict) and perfil_usuario.get("visitante") is True)
```


#### 📂 5. Anatomia do Payload JSON

> **Pergunta do professor:** Explicar a estrutura hierárquica do arquivo `static/data/viagens.json` (nó raiz com metadados, catálogo de provedores e nós por usuário).

**Resposta (o que falar):**

- O arquivo tem **três níveis**. **Nó raiz:** metadados do documento (`versao_schema`, `descricao`, `atualizado_em`, `total_usuarios`, `total_roteiros`). **Catálogo de provedores:** quais serviços alimentam os dados. **Nó `usuarios`:** um dicionário indexado pelo **id do usuário** (o `sub` do Google).
- Cada usuário tem `perfil` (id, nome, e-mail, foto), `metadados` (total de roteiros, criado e atualizado em) e a lista **`roteiros`**.
- Cada roteiro guarda: `id`, `criado_em`, `origem` e `destino` (texto), **`geolocalizacao`** (cidade, UF, latitude e longitude), **`telemetria`** (`clima` e `percurso`), `dicas_destino` (o guia), **`diagnostico_ia`** (status, modelo, se usou fallback e o motivo) e **`metadados.status_servicos`** (situação do geocoding e da IA).
- Indexar por id de usuário dá **acesso direto** aos roteiros de cada pessoa. O arquivo cria a estrutura padrão sozinho se não existir, e `viagens.json.example` traz o formato vazio.
- **Visitantes não aparecem** no arquivo: eles só existem em memória, e o endpoint `/viagens/json` os mescla apenas na resposta da sessão ativa.

**No código:** [`models/viagem_repository.py:39-54`](models/viagem_repository.py#L39-L54) — nó raiz e catálogo de provedores

```python
def criar_estrutura_padrao_viagens() -> dict[str, Any]:
    """Retorna a estrutura inicial do payload JSON de viagens com metadados e provedores."""
    return {
        "versao_schema": "1.0",
        "descricao": "Base consolidada de roteiros turísticos e telemetria por usuário",
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
        "total_usuarios": 0,
        "total_roteiros": 0,
        "provedores": {
            "geocoding": "Open-Meteo Geocoding API",
            "previsao_tempo": "Open-Meteo Forecast API",
            "roteamento": "OSRM Routing Engine",
            "inteligencia_artificial": "Google Gemini (gemini-3.6-flash)",
        },
        "usuarios": {},
    }
```

**No código:** [`models/viagem_repository.py:155-164`](models/viagem_repository.py#L155-L164) — nó de um usuário: perfil, metadados e roteiros

```python
        if user_id not in usuarios or not isinstance(usuarios[user_id], dict):
            usuarios[user_id] = {
                "perfil": perfil,
                "metadados": {
                    "total_roteiros": 0,
                    "criado_em": agora_iso,
                    "atualizado_em": agora_iso,
                },
                "roteiros": [],
            }
```

Exemplo (resumido):

```json
{
  "versao_schema": "1.0",
  "atualizado_em": "2026-09-25T15:23:16+00:00",
  "total_usuarios": 1,
  "total_roteiros": 1,
  "provedores": {
    "geocoding": "Open-Meteo Geocoding API",
    "previsao_tempo": "Open-Meteo Forecast API",
    "roteamento": "OSRM Routing Engine",
    "inteligencia_artificial": "Google Gemini (gemini-3.6-flash)"
  },
  "usuarios": {
    "<id do usuário>": {
      "perfil":    { "id": "...", "nome": "...", "email": "...", "foto": "..." },
      "metadados": { "total_roteiros": 1, "criado_em": "...", "atualizado_em": "..." },
      "roteiros": [
        {
          "id": "fdf022a3",
          "origem": "Teresina - PI",
          "destino": "Fortaleza - CE",
          "geolocalizacao": { "origem": { "cidade": "Teresina", "uf": "PI", "latitude": -5.089, "longitude": -42.801 },
                              "destino": { "...": "..." } },
          "telemetria": { "clima":    { "temperatura": "28.5 °C", "umidade": "40%", "vento": "12.0 km/h" },
                          "percurso": { "distancia": "592.0 km", "tempo": "8h 33min de carro", "modal": "carro" } },
          "dicas_destino": "🏛️ PONTOS TURÍSTICOS PRINCIPAIS\n...",
          "diagnostico_ia": { "status": "sucesso", "modelo": "gemini-2.5-flash", "fallback_utilizado": false },
          "metadados": { "status_requisicao": "sucesso",
                         "status_servicos": { "geocoding_origem": { "...": "..." }, "inteligencia_artificial": { "...": "..." } } }
        }
      ]
    }
  }
}
```


#### 🔒 6. Leitura e Escrita Thread-Safe

> **Pergunta do professor:** Explicar o uso do `threading.Lock()` para prevenir corrupção de dados por concorrência e a diferença entre `json.load/json.dump` e `json.loads/json.dumps`.

**Resposta (o que falar):**

- O Flask atende várias requisições ao mesmo tempo, em threads, e todas usam o **mesmo arquivo**. O perigo é a **condição de corrida** no ciclo *ler → alterar → salvar*: duas requisições leem a mesma versão, cada uma acrescenta a sua viagem e a **última a gravar apaga a da outra** (*lost update*), ou duas escritas se misturam e corrompem o JSON.
- A solução é o **lock**: só uma thread por vez executa o trecho protegido. O lock envolve o **ciclo inteiro** (`with lock_arquivo_json:` dentro de `adicionar_viagem_usuario`), e não só a leitura ou só a escrita separadamente.
- Usamos **`threading.RLock`** (lock **reentrante**) em vez de `Lock`: `adicionar_viagem_usuario` já segura o lock e chama `carregar_dados_viagens_json` e `salvar_dados_viagens_json`, que também o adquirem. Com um `Lock` comum, a própria thread ficaria esperando por si mesma (*deadlock*); o `RLock` permite readquirir na mesma thread.
- Comprovação: `test_gravacoes_simultaneas_nao_perdem_roteiros` faz 10 gravações simultâneas de usuários diferentes e **as 10 ficam salvas**.
- **`json.load` / `json.dump`** trabalham com **arquivo** (objeto de arquivo aberto); **`json.loads` / `json.dumps`** trabalham com **string** (o *s* é de *string*). Aqui usamos `load` e `dump` porque lemos e gravamos em disco. A resposta HTTP `/viagens/json` é serializada pelo `jsonify` do Flask (o equivalente a `dumps`).
- Em `json.dump` usamos `ensure_ascii=False` (mantém os acentos legíveis) e `indent=2` (arquivo formatado).
- **Limite honesto:** o lock protege as threads de **um processo**. Com vários processos (por exemplo `gunicorn` com vários workers) seria preciso lock de arquivo ou um banco de dados.

**No código:** [`models/viagem_repository.py:10-12`](models/viagem_repository.py#L10-L12) — o `RLock`

```python
# Controle de concorrência reentrante para leitura e escrita segura no arquivo JSON
DATA_DIR.mkdir(parents=True, exist_ok=True)
lock_arquivo_json = threading.RLock()
```

**No código:** [`models/viagem_repository.py:57-73`](models/viagem_repository.py#L57-L73) — leitura com lock e `json.load`

```python
def carregar_dados_viagens_json() -> dict[str, Any]:
    """Lê a base completa de viagens de static/data/viagens.json de forma thread-safe."""
    with lock_arquivo_json:
        if not VIAGENS_FILE.exists():
            return criar_estrutura_padrao_viagens()

        try:
            with VIAGENS_FILE.open("r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)

            if not isinstance(dados, dict):
                return criar_estrutura_padrao_viagens()

            return dados

        except (json.JSONDecodeError, OSError):
            return criar_estrutura_padrao_viagens()
```

**No código:** [`models/viagem_repository.py:95-101`](models/viagem_repository.py#L95-L101) — escrita com `json.dump`

```python
        with VIAGENS_FILE.open("w", encoding="utf-8") as arquivo:
            json.dump(
                dados_completos,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )
```

**No código:** [`models/viagem_repository.py:132-192`](models/viagem_repository.py#L132-L192) — o lock cobre o ciclo ler → alterar → salvar

```python
def adicionar_viagem_usuario(
    user_id: str,
    item: dict[str, Any],
    perfil_usuario: dict[str, Any] | None = None,
) -> None:
    """Adiciona um novo roteiro na memória do visitante ou no JSON do usuário logado."""
    with lock_arquivo_json:
        # Visitante: mantém os roteiros somente em memória (mesmo após reinício do servidor).
        if eh_usuario_visitante(user_id, perfil_usuario):
            viagens_visitante_memoria.setdefault(user_id, []).append(item)
            return

        # Usuário logado: recupera a base persistida.
        dados = carregar_dados_viagens_json()

        usuarios = dados.setdefault("usuarios", {})
        agora_iso = datetime.now(timezone.utc).isoformat()

        # Normaliza o perfil garantindo o campo 'foto' conforme schema
        perfil = dict(perfil_usuario or {})
        if "picture" in perfil and "foto" not in perfil:
            perfil["foto"] = perfil["picture"]

        if user_id not in usuarios or not isinstance(usuarios[user_id], dict):
            usuarios[user_id] = {
                "perfil": perfil,
                "metadados": {
                    "total_roteiros": 0,
                    "criado_em": agora_iso,
                    "atualizado_em": agora_iso,
                },
                "roteiros": [],
            }

        usuario = usuarios[user_id]

        if not usuario.get("perfil") and perfil:
            usuario["perfil"] = perfil

        # Migração defensiva: se o usuário continha a chave legada 'viagens', migra para 'roteiros'
        if "viagens" in usuario and "roteiros" not in usuario:
            usuario["roteiros"] = usuario.pop("viagens")

        roteiros = usuario.setdefault("roteiros", [])

        if not isinstance(roteiros, list):
            roteiros = []
            usuario["roteiros"] = roteiros

        roteiros.append(item)

        # Atualiza metadados do usuário conforme schema
        usuario["metadados"] = {
            "total_roteiros": len(roteiros),
            "criado_em": roteiros[0].get("criado_em", agora_iso) if roteiros else agora_iso,
            "atualizado_em": roteiros[-1].get("criado_em", agora_iso) if roteiros else agora_iso,
        }

        dados["total_usuarios"] = len(usuarios)

        salvar_dados_viagens_json(dados)
```


#### 🛡️ 7. Navegação Defensiva

> **Pergunta do professor:** Explicar o uso de `.get()` encadeado com valores padrão para prevenir exceções `KeyError` ao consumir dados aninhados.

**Resposta (o que falar):**

- `dados["usuarios"][id]["roteiros"]` lança **`KeyError`** se qualquer nível não existir (arquivo novo, usuário sem roteiros, JSON antigo ou editado à mão). O `.get(chave, padrão)` devolve o **padrão** em vez de lançar exceção.
- No projeto o `.get()` aparece **encadeado por nível**: `dados.get("usuarios", {})` → `usuarios.get(user_id, {})` → `usuario.get("roteiros")`. Cada passo já entrega algo seguro para o próximo (um dicionário vazio ou uma lista vazia).
- Além do `.get()`, há `isinstance(..., dict)` e `isinstance(..., list)` antes de cada nível: se o arquivo estiver corrompido (por exemplo `usuarios` virou uma lista), a função devolve `[]` em vez de quebrar.
- Também trata **formato antigo**: se não houver `roteiros`, tenta a chave legada `viagens`. E `roteiros[0].get("criado_em", agora_iso)` evita falhar se um roteiro não tiver a data.
- O mesmo cuidado está no login (`dados_usuario.get("name", "Usuário Google")`) e no clima (`dados.get("current", {})`).
- Resultado: a página inicial nunca dá erro 500 por causa de um dado ausente. Ela mostra a lista vazia.

**No código:** [`models/viagem_repository.py:104-129`](models/viagem_repository.py#L104-L129) — `.get()` encadeado com padrão e `isinstance` a cada nível

```python
def obter_viagens_usuario(user_id: str) -> list[dict[str, Any]]:
    """Recupera os roteiros do visitante em memória ou do usuário logado no JSON."""
    with lock_arquivo_json:
        if eh_usuario_visitante(user_id):
            return list(viagens_visitante_memoria.setdefault(user_id, []))

        dados = carregar_dados_viagens_json()

        usuarios = dados.get("usuarios", {})

        if not isinstance(usuarios, dict):
            return []

        usuario = usuarios.get(user_id, {})

        if not isinstance(usuario, dict):
            return []

        roteiros = usuario.get("roteiros")
        if roteiros is None:
            roteiros = usuario.get("viagens", [])

        if not isinstance(roteiros, list):
            return []

        return list(roteiros)
```

**No código:** [`models/viagem_repository.py:184-188`](models/viagem_repository.py#L184-L188) — `.get()` com data padrão

```python
        usuario["metadados"] = {
            "total_roteiros": len(roteiros),
            "criado_em": roteiros[0].get("criado_em", agora_iso) if roteiros else agora_iso,
            "atualizado_em": roteiros[-1].get("criado_em", agora_iso) if roteiros else agora_iso,
        }
```

**No código:** [`controllers/auth_controller.py:36-38`](controllers/auth_controller.py#L36-L38) — valores padrão ao ler o perfil do Google

```python
        "nome": dados_usuario.get("name", "Usuário Google"),
        "email": dados_usuario.get("email", ""),
        "foto": dados_usuario.get("picture", ""),
```


---
