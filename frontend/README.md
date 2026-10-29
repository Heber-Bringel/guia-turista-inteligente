# Frontend — Guia do Turista Inteligente

SPA React 19 + TypeScript da Unidade II. O cliente centraliza REST e SSE em `src/services/api.ts`, usa Leaflet para a rota e mantém sessões Google/visitante no navegador.

## Executar

```bash
cp .env.example .env
npm install
npm run dev
```

A aplicação abre em `http://localhost:5173` e usa a API em `http://localhost:8001/api/v1`.

## Variáveis

```env
VITE_API_URL=http://localhost:8001/api/v1
VITE_GOOGLE_CLIENT_ID=seu-client-id.apps.googleusercontent.com
```

## Qualidade

```bash
npm test
npm run lint
npm run typecheck
npm run build
```

## Contratos esperados

- `POST /auth/visitante` e `POST /auth/google`
- `POST /roteiros/planejar` e `POST /roteiros/mapa-rota`
- `POST /roteiros/stream-guia` (`text/event-stream`)
- `GET /roteiros/minhas-viagens`
- `DELETE /roteiros/{id}` e `PATCH /roteiros/{id}/visitas`
- `POST /roteiros/exportar/gpx`

O cliente envia `X-User-Id`, cookies da sessão e `Authorization` quando houver token. O adaptador do payload fica em um único ponto para facilitar o fechamento do contrato com o backend.
