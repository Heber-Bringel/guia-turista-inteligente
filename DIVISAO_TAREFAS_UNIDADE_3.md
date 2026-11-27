# Divisão de Tarefas — AT07 :: V3 Sistema Viajante com n8n

> **Curso:** Automação Web e Python — Unidade III (AT07)
> **Atividade:** V3 — Sistema Viajante em Arquitetura Orientada a Eventos (EDA) com n8n
> **Base da evolução:** V2 consolidada em `main` (`18ec0d0` — FastAPI + React 19/TypeScript + Leaflet + Open-Meteo + OSRM + Gemini)
> **Equipe:** Héber Bringel (`@Heber-Bringel`), Douglas Leone (`@DouglasLeone`) e Mikaelle Barroso (`@mikaelleBarroso`)
> **Carga horária estimada:** 6 horas

## 1. Objetivo e Regra para Equipe de Três Integrantes

Evoluir a plataforma **Guia do Turista Inteligente (V2)** conectando o ecossistema existente (**FastAPI + React 19/TypeScript + APIs geoespaciais/IA**) ao orquestrador **n8n** em uma **Arquitetura Orientada a Eventos (EDA)**.

O enunciado prevê equipes de 4 alunos. Mantendo o mesmo critério da Unidade II (`DIVISAO_TAREFAS_UNIDADE_2.md`), cada integrante continua responsável pelos módulos que já domina e os quatro workflows do n8n, os testes e as evidências em `docs/evidencias/` foram distribuídos de forma equilibrada entre os três:

| Papel previsto na V3 | Responsável na equipe | Adaptação na V3 |
|---|---|---|
| Aluno 1 — Frontend, i18n & UX Multicanal | **Héber Bringel** (`@Heber-Bringel`) | Pop-up ANP no mapa, chat conversacional Gemini, i18n (`Accept-Language`), higienização da UI, entrega multicanal (E-mail/WhatsApp) e **Workflow 3 (Despacho Multicanal)** |
| Aluno 2 — Dados Regulatórios ANP & IA Multilíngue | **Douglas Leone** (`@DouglasLeone`) | Consulta/ranqueamento regulatório de postos ANP, diálogo interativo multilíngue no Gemini (preservando patrimônios locais) e **Workflow 4 (Clima + Gemini)** |
| Aluno 3 — Backend Core EDA, DLQ & Segurança | **Mikaelle Barroso** (`@mikaelleBarroso`) | Contratos Pydantic v2, propagação de `Accept-Language`, DLQ com `BackgroundTasks`, proteção `X-Support-Key` e **Workflows 1 (DLQ) e 2 (ChatOps)** |
| Aluno 4 — Orquestração n8n, QA & Evidências | **Responsabilidade compartilhada** | Cada integrante exporta seus workflows em `n8n/workflows/`, executa sua suíte de testes e registra seus prints em `docs/evidencias/` + `README.md` |

Cada arquivo possui um responsável principal. Alterações em arquivos de outro integrante devem ser combinadas e revisadas por quem responde pelo módulo.

---

## 2. Visão Geral da Divisão

| Integrante | Frente principal (Evolução V2 → V3) | Workflows n8n sob responsabilidade | Entrega demonstrável |
|---|---|---|---|
| **Héber Bringel** | Frontend React/TS: Pop-up ANP por clique, Chat IA, i18n (`Accept-Language`), higienização da interface pública e entrega multicanal | **WF 3 — Despacho Multicanal** (`turismo-despachar-roteiro` → E-mail HTML transacional / WhatsApp) | Interface limpa sem métricas internas, seletor multilíngue, pop-up ANP por clique no marcador, diálogo com IA e entrega do roteiro por E-mail/WhatsApp |
| **Douglas Leone** | Serviços de dados: ranqueamento regulatório de postos ANP ao longo da rota (ex.: BR-343 em Piripiri) e Chat Gemini multilíngue contextual | **WF 4 — Clima e Orientações IA** (`Webhook` → Open-Meteo → avaliação chuva/temperatura → Gemini) | Postos ranqueados com dados regulatórios da ANP, diálogo IA considerando ritmo/acompanhantes/gastronomia preservando patrimônios locais e alerta climático via n8n |
| **Mikaelle Barroso** | Núcleo FastAPI EDA: `BackgroundTasks` para DLQ, endpoints de chat/despacho, proteção `X-Support-Key` e observabilidade restrita | **WF 1 — DLQ Telegram** (`turismo-dlq`) e **WF 2 — ChatOps Telegram** (`/status`, `/uptime`, `/telemetria`, `/testardlq`) | Falhas capturadas em background com UUID + stack trace no Telegram da equipe e comandos de suporte autenticados por `Chat ID` + `X-Support-Key` |

---

## 3. Héber Bringel (`@Heber-Bringel`) — Frontend V3, i18n, Pop-up ANP, Higienização e Workflow 3 (Despacho Multicanal)

### Arquivos sob responsabilidade

- `frontend/src/App.tsx`
- `frontend/src/components/MapaRota.tsx`
- `frontend/src/components/TelemetriaCard.tsx`
- `frontend/src/components/GuiaViajante.tsx` (e novo componente de Chat, ex.: `frontend/src/components/ChatRoteiro.tsx`)
- `frontend/src/components/Header.tsx` (seletor de idioma)
- `frontend/src/components/DespachoModal.tsx` (ou seção de envio E-mail / WhatsApp)
- `frontend/src/i18n/` (dicionários e helper de idioma para PT, EN, ES, FR, ZH, HI, AR, RU)
- `frontend/src/services/api.ts`
- `frontend/src/types/api.ts` e `frontend/src/types/roteiro.ts`
- Testes em `frontend/src/**/*.test.ts` e `frontend/src/**/*.test.tsx`
- `n8n/workflows/wf3-despacho-roteiro.json`

### Responsabilidades de implementação

1. **Pop-up regulatório de postos ANP (`MapaRota.tsx`)**:
   - Exibir os postos ranqueados ao longo da rota com pop-up ativado **exclusivamente por clique no marcador** (não abrir automaticamente ao passar o mouse ou ao carregar).
   - Mostrar no pop-up: **CNPJ**, **Razão Social**, **avaliação**, **tempo de autorização na ANP** e **combustíveis** disponíveis.
2. **Diálogo interativo com IA (Chat Gemini)**:
   - Evoluir o fluxo do guia para uma conversa com IA permitindo ao usuário informar **ritmo de viagem**, **acompanhantes** e **preferências de gastronomia** para construir e refinar o roteiro personalizado.
3. **Entrega multicanal exclusiva (E-mail e WhatsApp)**:
   - **Substituir o download manual direto (botão GPX)** em `App.tsx` pelo fluxo de despacho via **E-mail** (HTML transacional) e **WhatsApp**, acionando o endpoint do FastAPI que dispara o webhook `turismo-despachar-roteiro` no n8n.
   - Exibir feedback claro de envio em andamento, confirmação e erro amigável.
4. **Suporte a múltiplos idiomas (`Accept-Language`)**:
   - Adicionar seletor de idioma no `Header.tsx` com suporte a Português, Inglês (`en`), Espanhol (`es`), Francês (`fr`), Mandarim (`zh`), Hindi (`hi`), Árabe (`ar` — com suporte a direção `rtl` se aplicável) e Russo (`ru`).
   - Propagar automaticamente o cabeçalho HTTP `Accept-Language` em todas as chamadas de `frontend/src/services/api.ts`.
5. **Higienização da interface pública e degradação graciosa**:
   - Ocultar completamente do usuário comum métricas internas, traces (`X-Request-ID`), contagem de provedores ativos/indisponíveis e latências (`X-Process-Time`, tempo no navegador) em `TelemetriaCard.tsx` e `App.tsx`.
   - Em caso de falha de provedor ou erro interno, exibir mensagens acolhedoras e sem detalhes técnicos (o backend despacha o incidente para a DLQ em segundo plano).
6. **Workflow 3 no n8n — Despacho Multicanal**:
   - `Webhook` (`turismo-despachar-roteiro`) → nó `Switch`/`IF` de roteamento por canal (`email` vs `whatsapp`) → envio de **E-mail HTML transacional** (Gmail/Resend) ou **mensagem via API de WhatsApp** (Evolution API / WhatsApp Cloud API / webhook compatível).
7. **Qualidade no frontend**:
   - Atualizar e expandir testes em Vitest cobrindo pop-up ANP, envio do cabeçalho `Accept-Language`, higienização da UI, fluxo do chat e despacho multicanal.

### Contratos que deve combinar com a equipe

- **Com Mikaelle**: payload e rota de despacho multicanal (`POST /api/v1/roteiros/despachar`), payload do endpoint de chat (`POST /api/v1/roteiros/chat`), formato do cabeçalho `Accept-Language` e mensagens padronizadas de erro degradado.
- **Com Douglas**: campos exatos dos postos ANP (`cnpj`, `razao_social`, `avaliacao`, `tempo_autorizacao_anp`, `combustiveis`, `ranking_score`) e formato das mensagens/respostas do chat multilíngue.

### Critérios de aceite

- Pop-up de posto ANP abre exclusivamente ao clicar no marcador e exibe os 5 atributos regulatórios exigidos.
- Download manual direto (GPX) removido da interface pública e substituído pelo despacho por E-mail e WhatsApp via n8n.
- Nenhuma latência, UUID técnico, stack trace ou status interno de provedor aparece na tela do usuário comum.
- Trocar o idioma atualiza o cabeçalho `Accept-Language` enviado à API e retorna o diálogo no idioma escolhido preservando nomes de patrimônios locais.
- `npm test`, `npm run lint`, `npm run typecheck` e `npm run build` passam sem erros.

---

## 4. Douglas Leone (`@DouglasLeone`) — Postos ANP, Chat Gemini Multilíngue e Workflow 4 (Clima + IA)

### Arquivos sob responsabilidade

- `backend/app/services/postos_service.py` (e fonte/catálogo regulatório ANP em `backend/app/core/catalogo.py` ou `backend/app/services/anp_service.py`)
- `backend/app/services/gemini_service.py`
- `backend/app/services/clima_service.py`
- `backend/app/services/geo_utils.py`
- Testes unitários em `backend/tests/services/` (`test_postos_service.py`, `test_gemini_service.py`, `test_clima_service.py`, etc.)
- `n8n/workflows/wf4-clima-gemini.json`

### Responsabilidades de implementação

1. **Consulta e ranqueamento regulatório de postos ANP (`postos_service.py`)**:
   - Evoluir a localização de paradas ao longo da rota (incluindo o caso de referência **BR-343 em Piripiri - PI**) para consultar/cruzar dados regulatórios da ANP.
   - Retornar por posto: **CNPJ**, **Razão Social**, **avaliação**, **tempo de autorização na ANP** e **lista de combustíveis**.
   - Implementar fórmula clara e testável de **ranqueamento regulatório** (ex.: combinando tempo de autorização ANP, avaliação e proximidade da rota/trecho), mantendo fallback controlado caso a fonte externa falhe.
2. **Construção de roteiro via diálogo com IA (`gemini_service.py`)**:
   - Implementar serviço assíncrono de diálogo conversacional multi-turno (histórico de mensagens + contexto da viagem), incorporando explicitamente **ritmo de viagem**, **acompanhantes** e **gastronomia**.
   - Garantir que o diálogo produza um roteiro estruturado pronto para ser exibido no chat e enviado nos templates multicanal (E-mail/WhatsApp).
3. **Adaptação multilíngue contextual via `Accept-Language`**:
   - Interpretar o idioma recebido do `Accept-Language` (Português, Inglês, Espanhol, Francês, Mandarim, Hindi, Árabe, Russo, etc.) e adaptar todo o diálogo, instruções e fallback de contingência ao idioma solicitado.
   - **Regra obrigatória no prompt e nos testes**: preservar intactos os **nomes próprios de patrimônios locais** (ex.: *Parque Nacional de Sete Cidades*, *Serra da Capivara*, *Delta do Parnaíba*, *BR-343*, *Pelourinho*), sem traduzi-los literalmente.
4. **Workflow 4 no n8n — Clima + Orientações Gemini**:
   - `Webhook` (recebendo destino/coordenadas e idioma) → requisição HTTP à **Open-Meteo** → nó de avaliação de **chuva e temperatura** (regras/limiares claros) → geração de **orientações práticas via Gemini** (nó HTTP/AI) → retorno estruturado para consumo/alerta.
5. **Testes determinísticos**:
   - Cobrir ranqueamento ANP (incluindo trecho BR-343 em Piripiri), diálogo multi-turno (ritmo, acompanhantes, gastronomia) e preservação de nomes de patrimônios locais em múltiplos idiomas sem chamadas reais de rede.

### Contratos que deve combinar com a equipe

- **Com Mikaelle**: assinaturas assíncronas dos serviços de postos ANP e chat Gemini, propagação de exceções para a DLQ quando houver falha crítica e leitura do idioma parseado de `Accept-Language`.
- **Com Héber**: estrutura JSON dos postos ANP para o pop-up do mapa e estrutura do histórico de mensagens do chat + resumo do roteiro para o despacho multicanal.

### Critérios de aceite

- Postos ao longo da rota retornam ranqueados com CNPJ, Razão Social, avaliação, tempo de autorização ANP e combustíveis (caso BR-343 em Piripiri coberto por teste).
- Prompt multilíngue responde no idioma de `Accept-Language` (EN, ES, FR, ZH, HI, AR, RU, PT) preservando nomes de patrimônios locais.
- Workflow 4 ativo no n8n consulta Open-Meteo, avalia chuva/temperatura e produz orientação via Gemini.
- `pytest backend/tests/services -v` passa integralmente offline.

---

## 5. Mikaelle Barroso (`@mikaelleBarroso`) — Núcleo FastAPI EDA, DLQ em BackgroundTasks, ChatOps e Workflows 1 e 2

### Arquivos sob responsabilidade

- `backend/app/main.py`
- `backend/app/core/config.py` (URLs de webhooks n8n, `SUPPORT_API_KEY`, tempo de início para uptime)
- `backend/app/core/dependencies.py` (validação de `X-Support-Key` e extração/normalização de `Accept-Language`)
- `backend/app/core/logging_config.py`
- `backend/app/schemas/roteiros.py` (novos schemas para postos ANP, chat IA, despacho multicanal e payloads de suporte)
- `backend/app/routers/roteiros.py` (rotas de chat, despacho multicanal via n8n, remoção/restrição do download manual direto e integração DLQ)
- `backend/app/routers/telemetria.py` (e/ou novo `backend/app/routers/suporte.py` para `/status`, `/uptime`, `/telemetria`, `/testardlq`)
- `backend/app/services/n8n_service.py` (cliente assíncrono para despacho de eventos aos webhooks `turismo-dlq`, `turismo-despachar-roteiro` e clima)
- Testes de integração em `backend/tests/test_roteiros.py`, `backend/tests/test_telemetria.py`, `backend/tests/test_suporte.py` e `backend/tests/test_dlq.py`
- `n8n/workflows/wf1-dlq-telegram.json` e `n8n/workflows/wf2-chatops-telegram.json`

### Responsabilidades de implementação

1. **Arquitetura Orientada a Eventos (`n8n_service.py` + `BackgroundTasks`)**:
   - Centralizar o disparo assíncrono de eventos HTTP para os webhooks do n8n reaproveitando o `httpx.AsyncClient` compartilhado em `app.state.http_client` com timeouts defensivos.
   - Garantir registro explícito nos logs do FastAPI comprovando o agendamento e a execução em `BackgroundTasks` (necessário para o entregável de evidências).
2. **DLQ (Dead Letter Queue) com degradação graciosa**:
   - Capturar falhas internas/de provedores no backend sem vazar stack trace ou erro cru ao frontend.
   - Gerar **UUID de rastreio** (`trace_id`), registrar log estruturado e despachar em `BackgroundTasks` o payload de incidente (UUID, serviço/rota, mensagem, timestamp, `stack_trace`) para o webhook `turismo-dlq` do n8n.
3. **Segurança e Observabilidade Restrita (ChatOps)**:
   - Proteger os endpoints operacionais (`/api/v1/suporte/status`, `/api/v1/suporte/uptime`, `/api/v1/telemetria`, `/api/v1/suporte/testardlq`) com dependência obrigatória validando o cabeçalho **`X-Support-Key`** (retornando `401`/`403` quando ausente ou inválido).
   - Implementar o endpoint **`/testardlq`** que simula uma falha controlada, retorna resposta degradada limpa e dispara um incidente real via `BackgroundTasks` para o webhook `turismo-dlq`.
   - Calcular `uptime` real da aplicação desde o `lifespan` em `main.py`.
4. **Novas rotas e contratos V3 (`roteiros.py` e `schemas/roteiros.py`)**:
   - Extrair e propagar `Accept-Language` nas rotas de planejamento e chat.
   - Expor `POST /api/v1/roteiros/chat` (integrando o serviço de diálogo do Douglas).
   - Expor `POST /api/v1/roteiros/despachar` (validando canal `email` ou `whatsapp`, destinatário e roteiro, despachando via `BackgroundTasks` para `turismo-despachar-roteiro` no n8n).
   - Higienizar respostas públicas para não expor métricas internas ou stack traces ao usuário final.
5. **Workflow 1 no n8n — DLQ Telegram**:
   - `Webhook` (`turismo-dlq`) → nó **`Code`** (formatação limpa em Markdown com UUID de rastreio, rota, horário e trecho formatado do stack trace) → envio de alerta **Markdown no Telegram** da equipe técnica.
6. **Workflow 2 no n8n — Bot ChatOps Telegram**:
   - `Telegram Trigger` → validação estrita de **`Chat ID`** autorizado (bloqueando/ignorando remetentes não autorizados) → nó **`Switch`** para `/status`, `/uptime`, `/telemetria` e `/testardlq` → requisição HTTP autenticada ao FastAPI enviando **`X-Support-Key`** → envio da resposta formatada no chat do Telegram.
7. **Testes de integração**:
   - Cobrir autenticação `X-Support-Key` (sucesso e recusa), disparo da DLQ via `BackgroundTasks` (inclusive via `/testardlq`), propagação de `Accept-Language`, rotas de chat e despacho multicanal.

### Contratos que deve combinar com a equipe

- **Com Héber**: rotas e schemas de chat, despacho multicanal, cabeçalho `Accept-Language` e contrato do webhook `turismo-despachar-roteiro`.
- **Com Douglas**: schema dos postos ANP em `RoteiroResponse`, interface do serviço de chat multilíngue e integração opcional do webhook de clima.

### Critérios de aceite

- Endpoints de suporte (`/status`, `/uptime`, `/telemetria`, `/testardlq`) rejeitam chamadas sem `X-Support-Key` válido.
- Falhas simuladas via `/testardlq` (ou exceções internas) não expõem stack trace ao cliente, geram log de execução em `BackgroundTasks` e chegam formatadas em Markdown no Telegram com UUID de rastreio.
- Bot Telegram responde aos 4 comandos apenas para o `Chat ID` autorizado.
- `pytest backend/tests -v` passa sem depender de internet ou serviços externos reais.

---

## 6. Contratos e Variáveis de Ambiente da V3

Antes de avançar em paralelo, a equipe deve alinhar estas variáveis em `.env.example` e contratos HTTP:

### Variáveis de ambiente novas (`.env.example`)

```env
# Segurança operacional (ChatOps / Suporte)
SUPPORT_API_KEY=troque-por-uma-chave-segura-de-suporte

# Integração n8n (Webhooks)
N8N_BASE_URL=http://localhost:5678
N8N_WEBHOOK_DLQ=/webhook/turismo-dlq
N8N_WEBHOOK_DESPACHAR_ROTEIRO=/webhook/turismo-despachar-roteiro
N8N_WEBHOOK_CLIMA=/webhook/turismo-clima
```

### Contratos principais a fechar no início

| Interface / Evento | Responsável por propor | Quem valida |
|---|---|---|
| Schema de posto ANP (`cnpj`, `razao_social`, `avaliacao`, `tempo_autorizacao_anp`, `combustiveis`, `ranking_score`) | Douglas | Héber e Mikaelle |
| `POST /api/v1/roteiros/chat` + cabeçalho `Accept-Language` | Mikaelle | Douglas e Héber |
| `POST /api/v1/roteiros/despachar` + payload `turismo-despachar-roteiro` | Mikaelle | Héber |
| Payload `turismo-dlq` (`trace_id`, `rota`, `erro`, `stack_trace`, `timestamp`) | Mikaelle | Héber e Douglas |
| Endpoints ChatOps (`/status`, `/uptime`, `/telemetria`, `/testardlq`) + `X-Support-Key` | Mikaelle | Douglas e Héber |
| Payload Webhook Clima → Open-Meteo → Gemini (WF 4) | Douglas | Mikaelle |

---

## 7. Sequência de Integração (Sugestão para 6 horas)

1. **Hora 1 — Contratos e ambiente n8n**: fechar schemas Pydantic/TypeScript, subir o n8n (local/Docker) e validar conectividade FastAPI ↔ n8n e bot do Telegram.
2. **Horas 2 e 3 — Implementação paralela dos núcleos**:
   - **Mikaelle**: `n8n_service.py`, `BackgroundTasks` DLQ, rotas protegidas por `X-Support-Key` e WF 1 + WF 2 no n8n.
   - **Douglas**: serviço de postos ANP (BR-343 / Piripiri), chat Gemini multilíngue (preservando patrimônios locais) e WF 4 no n8n.
   - **Héber**: pop-up ANP por clique no `MapaRota.tsx`, higienização do `TelemetriaCard.tsx`, seletor i18n (`Accept-Language`), tela do chat e modal de despacho multicanal.
3. **Hora 4 — Integração ponta a ponta**: conectar frontend → FastAPI → n8n (WF 3 de despacho E-mail/WhatsApp + WF 4 de clima + WF 1 DLQ + WF 2 ChatOps).
4. **Hora 5 — Testes e evidências**: rodar `pytest` e `vitest`/`build`, testar os cenários reais (BR-343 Piripiri, chat em outro idioma, `/testardlq`, comandos ChatOps, envio de roteiro) e salvar todos os 7 prints em `docs/evidencias/`.
5. **Hora 6 — Documentação e entrega**: exportar os JSONs dos 4 workflows para `n8n/workflows/`, atualizar o `README.md` com a arquitetura V3 e as evidências, revisar PRs e validar o fluxo completo.

---

## 8. Estratégia de Branches e Revisão

| Integrante | Branch sugerida | Revisão principal |
|---|---|---|
| **Héber** | `feat/v3-frontend-anp-i18n-multicanal` | Mikaelle valida contratos REST e higienização; Douglas valida pop-up ANP e chat |
| **Douglas** | `feat/v3-anp-gemini-multilingue-wf4` | Mikaelle valida integração assíncrona; Héber valida dados do pop-up e respostas do chat |
| **Mikaelle** | `feat/v3-backend-eda-dlq-chatops` | Héber valida rotas e despacho; Douglas valida propagação de `Accept-Language` e erros |
| **Equipe** | `docs/v3-evidencias-e-readme` | Todos conferem os 7 entregáveis em `docs/evidencias/` e os JSONs de workflows |

---

## 9. Checklist de Entregáveis (`docs/evidencias/` + `README.md`)

Todas as evidências devem ser salvas em `docs/evidencias/` e referenciadas no `README.md`:

- [ ] `docs/evidencias/01-workflows-ativos-n8n.png` — Workflows ativos no n8n (WF 1, WF 2, WF 3 e WF 4). *(Equipe)*
- [ ] `docs/evidencias/02-alerta-dlq-telegram.png` — Alerta de incidente da DLQ no Telegram (Markdown, UUID de rastreio e stack trace). *(Mikaelle)*
- [ ] `docs/evidencias/03-chatops-telegram.png` — Resposta de comando ChatOps no Telegram (`/status`, `/uptime`, `/telemetria`, `/testardlq`). *(Mikaelle)*
- [ ] `docs/evidencias/04-popup-posto-anp-mapa.png` — Pop-up de posto ANP no mapa interativo (aberto por clique no marcador, ex.: BR-343 em Piripiri). *(Héber + Douglas)*
- [ ] `docs/evidencias/05-dialogo-multilingue-gemini.png` — Diálogo multilíngue no Chat Gemini preservando nomes de patrimônios locais. *(Héber + Douglas)*
- [ ] `docs/evidencias/06-roteiro-entregue-multicanal.png` — Roteiro entregue por E-mail (HTML transacional) ou WhatsApp via n8n. *(Héber)*
- [ ] `docs/evidencias/07-logs-fastapi-backgroundtasks.png` — Logs do FastAPI comprovando execução em `BackgroundTasks`. *(Mikaelle)*
- [ ] JSONs dos 4 workflows exportados e versionados em `n8n/workflows/`. *(Equipe)*
- [ ] `README.md` atualizado documentando a arquitetura V3 (EDA com n8n), setup e todas as evidências. *(Equipe)*
