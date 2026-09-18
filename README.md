# 🇧🇷 Guia do Turista Inteligente (Flask + HTTPX + Google Auth + Gemini AI)

Aplicação web desenvolvida com o microframework **Flask** e Python moderno para orquestração de APIs externas, gerando roteiros de viagem com dados meteorológicos, cálculo de percurso rodoviário e guia turístico & culinário com inteligência artificial.

---

## 🚀 Como Executar o Projeto Localmente

### 1. Clonar o Repositório

```bash
git clone https://github.com/SEU_USUARIO/guia-turista-inteligente.git
cd guia-turista-inteligente
```

---

### 2. Criar e Ativar o Ambiente Virtual (`.venv`)

=== "Linux / macOS"
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

=== "Windows (PowerShell)"
    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```

---

### 3. Instalar as Dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Configurar as Chaves e Variáveis de Ambiente

Configure as variáveis no seu terminal:

```bash
export GEMINI_API_KEY="SUA_CHAVE_GEMINI_AQUI"
export GOOGLE_CLIENT_ID="776335673676-pvie3ppdt9oe2r6ja7jckb3vqkv523em.apps.googleusercontent.com"
export PORT="8001"
```

> **Obtenção da Chave Gemini:** Acesse o [Google AI Studio](https://aistudio.google.com/), crie sua chave e defina na variável `GEMINI_API_KEY`.

---

### 5. Iniciar o Servidor Flask

```bash
python app.py
```

Acesse a aplicação no navegador em:
👉 **`http://localhost:8001`**

---

## 📂 Estrutura do Projeto

```text
├── app.py                 # Aplicação Flask (Rotas REST: GET /, GET /api/viagens, POST /api/viagens, DELETE /api/viagens/<id>)
├── config.py              # Constantes, UFs do Brasil e variáveis de ambiente
├── services.py            # Integrações com APIs externas via HTTPX (Open-Meteo, OSRM, Google OAuth)
├── planejamento.py        # Módulo de IA Gemini para geração de guia turístico e gastronomia
├── templates/
│   └── index.html         # Frontend SPA moderno com Google Identity, Cards e Accordion
├── requirements.txt       # Lista de dependências Python
└── README.md              # Documentação e instruções de execução
```

---

## 🧪 Qualidade de Código e Linter

Para validar o código com as ferramentas da disciplina:

```bash
# Formatação e checagem de boas práticas (PEP 8)
ruff check . --fix

# Checagem estática de tipos (Type Hints)
mypy app.py services.py planejamento.py config.py
```
