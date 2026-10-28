# Divisão de Tarefas — Unidade II: FastAPI, React e TypeScript

> **Curso:** Automação Web e Python — Unidade II
> **Atividade:** Guia do Turista Inteligente — Microsserviço FastAPI e SPA React 19 com TypeScript
> **Equipe:** Héber Bringel, Douglas Leone e Mikaelle Barroso
> **Enunciado:** [Atividade 2 — Guia do Turista Inteligente](https://maykolsampaio.github.io/cursos-maykol/cursos/automacao-web-python/unidade-2/atividade-2/)

## 1. Regra adotada para a equipe de três pessoas

O enunciado distribui a apresentação entre quatro papéis. Como a equipe continua com três integrantes, os três primeiros papéis foram adaptados às especialidades já exercidas na Unidade I, enquanto as responsabilidades do **Aluno 4 — DevOps, QA e Streaming** foram incorporadas aos respectivos módulos:

| Papel previsto no enunciado | Responsável na equipe | Adaptação |
|---|---|---|
| Aluno 1 — Frontend Developer | **Héber Bringel** | SPA React com TypeScript, integração REST/SSE, mapa, geolocalização e sessão híbrida |
| Aluno 2 — Backend Core Engineer | **Mikaelle Barroso** | FastAPI, contratos, orquestração assíncrona, concorrência, persistência e telemetria |
| Aluno 3 — Data & Altimetry Engineer | **Douglas Leone** | APIs geoespaciais, altimetria, autonomia, custos, Gemini, streaming e GPX |
| Aluno 4 — DevOps, QA & Streaming Lead | **Responsabilidade compartilhada** | Héber testa o frontend; Douglas responde por SSE/GPX; Mikaelle responde por métricas e testes do backend |

Cada arquivo possui um responsável principal. Alterações em arquivos de outro integrante devem ser revisadas por quem responde por aquele módulo.

## 2. Visão geral da divisão

| Integrante | Frente principal | Entrega demonstrável |
|---|---|---|
| **Héber Bringel** | Frontend React com TypeScript, mapa e sessão híbrida | Usuário entra como visitante ou Google, planeja a viagem e visualiza rota, telemetria e histórico em uma SPA responsiva e tipada |
| **Douglas Leone** | Dados de viagem, custos, IA e exportação | Rota enriquecida com clima, relevo, autonomia e custos; guia conciso transmitido por SSE; arquivo GPX válido |
| **Mikaelle Barroso** | Núcleo FastAPI, concorrência e persistência | API validada por Pydantic, pipeline assíncrono, idempotência, cancelamento, histórico isolado e métricas operacionais |

## 3. Héber Bringel — Frontend React com TypeScript, mapa e sessão híbrida

### Arquivos sob responsabilidade

- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/index.css`
- `frontend/src/types/api.ts`
- `frontend/src/types/roteiro.ts`
- `frontend/src/services/api.ts`
- `frontend/src/services/geolocation.ts`
- `frontend/src/components/Header.tsx`
- `frontend/src/components/RoteiroForm.tsx`
- `frontend/src/components/MapaRota.tsx`
- `frontend/src/components/TelemetriaCard.tsx`
- `frontend/src/components/HistoricoViagens.tsx`
- `frontend/src/components/GuiaViajante.tsx`
- `frontend/vite.config.ts` e `frontend/tsconfig.json`
- Testes de componentes e serviços em `frontend/src/**/*.test.tsx` e `frontend/src/**/*.test.ts`

### Responsabilidades de implementação

1. Criar a SPA com React 19, Vite e TypeScript em modo estrito, consumindo a API configurada por variável de ambiente.
2. Implementar o formulário de planejamento com origem, destino, estilo de viagem, dias, preferência de rota, veículo, consumo, autonomia e passageiros.
3. Centralizar as chamadas REST em `services/api.ts`, enviando `Content-Type`, credencial de sessão e `X-User-Id` quando o contrato final exigir.
4. Representar em `types/` os contratos da API, estados parciais, eventos SSE e propriedades dos componentes, sem usar `any` para contornar dados desconhecidos.
5. Consumir corretamente o streaming SSE com `ReadableStream`, preservando eventos divididos entre pacotes e encerrando a leitura quando `done` for recebido.
6. Implementar o mapa Leaflet com traçado da rota, alternativas e marcadores das paradas sugeridas.
7. Usar a Geolocation API e o cálculo de Haversine para alertar quando o usuário estiver a mais de 400 km da origem informada.
8. Implementar a sessão híbrida: Google, visitante e restauração da conta salva sem novo login.
9. Exibir estados de carregamento, erro, lista vazia e indisponibilidade parcial de provedores.
10. Garantir layout responsivo, navegação por teclado, contraste legível e suporte a movimento reduzido.
11. Cobrir com Vitest os fluxos de formulário, consumo da API, SSE, Haversine e atualização do histórico.

### Contratos que deve combinar com a equipe

- Com Mikaelle: payloads, cabeçalhos, códigos HTTP, mensagens de validação e rotas da API.
- Com Douglas: formato das coordenadas, geometria GeoJSON, paradas, altimetria, custos, clima e eventos SSE.

### O que Héber deve demonstrar e explicar

- Fluxo completo da SPA na porta `5173`.
- Separação entre estado da interface e dados recebidos da API.
- Tipagem dos contratos, propriedades, eventos e estados da aplicação, incluindo tratamento seguro de respostas desconhecidas.
- Diferença entre requisição REST comum e leitura progressiva do SSE.
- Uso de latitude/longitude no Haversine e regra do alerta acima de 400 km.
- Renderização de geometria e marcadores no Leaflet.
- Persistência e restauração da sessão híbrida no navegador.
- Testes Vitest dos componentes e serviços de frontend.

### Critérios de aceite da entrega

- Nenhum endpoint fica escrito diretamente em vários componentes; o acesso passa por `services/api.ts`.
- O projeto usa `strict: true`, evita `any` e passa na verificação do TypeScript sem emitir arquivos.
- O botão de planejamento impede envios repetidos e apresenta progresso.
- Erros 401, 409, 422 e 503 são traduzidos em mensagens úteis.
- O mapa enquadra a rota completa e funciona em celular e desktop.
- O leitor SSE não perde caracteres nem duplica fragmentos.
- `npm test`, `npm run lint`, `npm run typecheck` e `npm run build` terminam com sucesso.

## 4. Douglas Leone — Serviços de dados, altimetria, custos, IA e GPX

### Arquivos sob responsabilidade

- `backend/app/services/geocoding_service.py`
- `backend/app/services/clima_service.py`
- `backend/app/services/rota_service.py`
- `backend/app/services/altimetria_service.py`
- `backend/app/services/postos_service.py`
- `backend/app/services/custos_service.py`
- `backend/app/services/gemini_service.py`
- `backend/app/services/gpx_service.py`
- Catálogo curado usado pelos serviços, quando houver: `backend/app/core/catalogo.py`
- Testes unitários dos serviços em `backend/tests/services/`

### Responsabilidades de implementação

1. Migrar as integrações externas para funções assíncronas que reutilizam o `httpx.AsyncClient` recebido por injeção.
2. Geocodificar origem e destino no Brasil, respeitando a UF e tratando cidades homônimas.
3. Consultar clima e rota OSRM, retornando unidades numéricas e geometria compatível com o Leaflet.
4. Calcular o perfil altimétrico, ganho, perda, altitude máxima e impacto estimado do relevo no consumo.
5. Calcular combustível ou energia, pedágios, emissões estimadas, custo total e rateio por passageiro.
6. Projetar paradas conforme autonomia e margem de segurança, deixando explícito quando forem apenas posições estimadas e não postos confirmados.
7. Construir o prompt conciso do Gemini: identidade local, manhã, tarde, noite, gastronomia e orientação prática relacionada ao clima.
8. Implementar o gerador assíncrono usado pelo endpoint SSE, com fallback quando chave, cota ou provedor estiver indisponível.
9. Exportar rota e paradas em GPX 1.1 bem formado, com caracteres especiais escapados corretamente.
10. Criar testes determinísticos com APIs simuladas, sem depender de internet ou chave real.

### Contratos que deve combinar com a equipe

- Com Mikaelle: assinaturas dos serviços, modelos Pydantic, política de timeout, fallback e circuit breaker.
- Com Héber: ordem das coordenadas, formato da geometria, dados de telemetria, chunks SSE e arquivo GPX.

### O que Douglas deve demonstrar e explicar

- Concorrência das consultas externas e reaproveitamento do pool HTTP.
- Ordem `longitude, latitude` no OSRM/GeoJSON e conversão para o Leaflet.
- Cálculo de relevo, autonomia, custo e rateio.
- Limites da estimativa de pedágios, emissões e pontos de parada.
- Engenharia de prompt e resposta curta do guia turístico.
- Diferença entre devolver o texto completo e produzir chunks com gerador assíncrono.
- Estrutura do XML GPX 1.1 e abertura do arquivo por um aplicativo compatível.

### Critérios de aceite da entrega

- Todas as chamadas externas possuem timeout e falha controlada.
- Serviços não criam clientes HTTP próprios a cada chamada.
- O sistema continua utilizável quando clima, altimetria ou Gemini falham.
- Cálculos possuem unidades e regras documentadas e são cobertos por testes.
- O guia respeita os limites de concisão pedidos no enunciado.
- O GPX gerado é XML válido e contém rota e waypoints previstos.

## 5. Mikaelle Barroso — Núcleo FastAPI, contratos, concorrência e persistência

### Arquivos sob responsabilidade

- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/dependencies.py`
- `backend/app/core/logging_config.py`
- `backend/app/core/cache.py`
- `backend/app/core/circuit_breaker.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/roteiros.py`
- `backend/app/routers/auth.py`
- `backend/app/routers/roteiros.py`
- `backend/app/routers/telemetria.py`
- `backend/app/services/storage_service.py`
- Testes de integração em `backend/tests/test_roteiros.py`, `backend/tests/test_auth.py` e `backend/tests/test_telemetria.py`

### Responsabilidades de implementação

1. Configurar o FastAPI com `lifespan`, pool compartilhado de `httpx.AsyncClient`, CORS restrito às origens do frontend e documentação OpenAPI.
2. Modelar contratos Pydantic v2 estritos, com limites numéricos, campos obrigatórios, UF válida e rejeição de atributos inesperados.
3. Implementar autenticação Google e visitante, isolamento de usuário e dependências reutilizáveis.
4. Orquestrar `/api/v1/roteiros/planejar` em estágios: geocodificação paralela; clima e rota em paralelo; depois relevo, custos e composição da resposta.
5. Verificar `request.is_disconnected()` nos pontos relevantes e cancelar trabalho que não precisa mais ser concluído.
6. Proteger requisições equivalentes com `asyncio.Lock` e responder `HTTP 409` para duplicidade em andamento, removendo a chave também em caso de erro.
7. Persistir o histórico em tarefa de segundo plano, com escrita atômica, lock e isolamento por usuário.
8. Implementar listagem, exclusão e marcação de atrativos visitados sem expor dados de outro usuário.
9. Criar correlation ID, cabeçalho `X-Process-Time`, health checks, readiness e métricas Prometheus.
10. Cobrir contratos, autenticação, isolamento, concorrência, erros, persistência e métricas com Pytest.

### Contratos que deve combinar com a equipe

- Com Douglas: interfaces assíncronas dos serviços e representação padronizada de falhas parciais.
- Com Héber: OpenAPI, política CORS, autenticação, rotas, payloads e códigos de resposta.

### O que Mikaelle deve demonstrar e explicar

- Diferença entre WSGI síncrono e ASGI assíncrono no contexto do projeto.
- Ciclo de vida do cliente HTTP compartilhado e injeção de dependências.
- Dois estágios de `asyncio.gather()` e impacto na latência.
- Validação automática do Pydantic e resposta HTTP 422.
- Bloqueio com `asyncio.Lock`, conflito HTTP 409 e limpeza no bloco `finally`.
- Detecção de desconexão, tarefas em segundo plano e escrita atômica.
- Métricas, probes e testes de integração do backend.

### Critérios de aceite da entrega

- `/docs`, `/redoc`, `/healthz`, `/readyz` e `/metrics` respondem corretamente.
- Dados inválidos retornam 422; duplicidade ativa retorna 409; ausência de autenticação retorna 401.
- Um usuário não consegue ler, alterar ou excluir roteiro de outro.
- A chave de idempotência sempre é liberada, inclusive após exceção ou cancelamento.
- A persistência concorrente não perde registros nem produz JSON parcial.
- `pytest backend/tests -v` termina com sucesso sem chamadas reais aos provedores.

## 6. Interfaces entre as três entregas

Antes da implementação, a equipe deve fechar e versionar estes contratos:

| Interface | Responsável por propor | Quem valida |
|---|---|---|
| `POST /api/v1/roteiros/planejar` | Mikaelle | Héber e Douglas |
| Resposta de rota, telemetria, altimetria, custos e paradas | Douglas | Héber e Mikaelle |
| Autenticação Google/visitante e cabeçalhos da sessão | Mikaelle | Héber |
| Eventos de `/stream-guia` | Douglas | Héber e Mikaelle |
| Histórico, exclusão e marcação de visitas | Mikaelle | Héber |
| Download GPX | Douglas | Héber |
| Mensagens de erro e estados parciais | Mikaelle | Héber e Douglas |

Formato mínimo proposto para o SSE:

```text
data: {"chunk":"trecho recebido","done":false}

data: {"chunk":"","done":true}

```

O formato definitivo deve aparecer no OpenAPI ou na documentação do endpoint antes de frontend e backend avançarem de forma independente.

## 7. Sequência de integração

1. **Contrato primeiro:** Mikaelle publica schemas e exemplos de resposta; Douglas confirma os campos de serviços; Héber cria os tipos TypeScript e os mocks do frontend.
2. **Tracer bullet:** visitante → planejar rota simples → mostrar resultado no React, ainda sem IA, relevo ou histórico.
3. **Dados avançados:** Douglas conecta altimetria, custos, autonomia e GPX; Héber adiciona mapa e painéis correspondentes.
4. **Concorrência e resiliência:** Mikaelle integra `asyncio.gather`, lock, cancelamento, circuit breaker e persistência.
5. **Streaming:** Douglas entrega o gerador SSE; Mikaelle expõe o endpoint; Héber implementa a leitura progressiva.
6. **Sessão e histórico:** Mikaelle entrega autenticação e isolamento; Héber conclui sessão híbrida e histórico reativo.
7. **Qualidade final:** cada integrante conclui seus testes; a equipe executa as duas suítes e ensaia a demonstração integrada.

## 8. Estratégia de branches e revisão

| Integrante | Branch sugerida | Revisão principal |
|---|---|---|
| Héber | `feat/frontend-react-mapa` | Mikaelle valida contrato; Douglas valida dados no mapa |
| Douglas | `feat/servicos-dados-ia` | Mikaelle valida integração assíncrona; Héber valida payload visual |
| Mikaelle | `feat/backend-fastapi-core` | Douglas valida serviços; Héber valida API e CORS |

Commits devem ser pequenos e identificar o módulo, por exemplo: `feat(frontend): renderiza rota no Leaflet`, `feat(servicos): calcula perfil altimétrico` e `feat(api): orquestra planejamento assíncrono`.

## 9. Divisão da apresentação

A apresentação total deve permanecer entre 20 e 30 minutos. Uma divisão equilibrada para três pessoas é:

| Ordem | Integrante | Tempo sugerido | Demonstração e defesa |
|---|---|---:|---|
| 1 | **Héber** | 7–8 min | SPA TypeScript, contratos tipados, sessão híbrida, formulário, mapa, Haversine, histórico e testes Vitest |
| 2 | **Mikaelle** | 7–8 min | FastAPI, Pydantic, `asyncio.gather`, lock, cancelamento, persistência, métricas e Pytest |
| 3 | **Douglas** | 7–8 min | Clima, rota, relevo, autonomia, custos, Gemini/SSE, GPX e testes dos serviços |
| Encerramento | **Equipe** | 2–4 min | Fluxo ponta a ponta, resultados das suítes e arguição do professor |

Cada integrante deve fazer os commits dos arquivos que defenderá e dominar as decisões, cálculos, falhas e limitações de sua parte.

## 10. Checklist conjunto de conclusão

- [ ] Backend e frontend executam em projetos independentes nas portas `8001` e `5173`.
- [ ] Contratos REST e SSE estão documentados e usados sem duplicação de formatos.
- [ ] A rota principal usa concorrência assíncrona e apresenta tempo de processamento.
- [ ] A interface exibe mapa, clima, relevo, autonomia, custos, histórico e guia progressivo.
- [ ] Login Google, visitante e restauração da sessão funcionam.
- [ ] Histórico e operações de roteiro respeitam o isolamento entre usuários.
- [ ] Falhas de provedores geram degradação controlada, sem derrubar todo o planejamento.
- [ ] GPX é válido e abre em uma ferramenta compatível.
- [ ] Backend passa em Pytest; frontend passa em Vitest, lint, verificação TypeScript e build.
- [ ] Os três integrantes ensaiaram exclusivamente o código que irão defender.
