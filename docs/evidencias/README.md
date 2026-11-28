# Evidências da V3 (AT07 — Sistema Viajante com n8n)

Salve cada print **com o nome exato** abaixo nesta pasta. O `README.md` da raiz já aponta para esses arquivos.

| # | Arquivo | Responsável | Como gerar |
|---|---|---|---|
| 01 | `01-workflows-ativos-n8n.png` | Equipe | Painel do n8n (`http://localhost:5678`) com WF 1, WF 2, WF 3 e WF 4 importados e **ativos**. |
| 02 | `02-alerta-dlq-telegram.png` | Mikaelle | Chamar `GET /api/v1/suporte/testardlq` com `X-Support-Key` (ou `/testardlq` no bot) e capturar o alerta em Markdown no Telegram, com UUID de rastreio e stack trace. |
| 03 | `03-chatops-telegram.png` | Mikaelle | No chat autorizado do Telegram, enviar `/status`, `/uptime` ou `/telemetria` e capturar a resposta do bot. |
| 04 | `04-popup-posto-anp-mapa.png` | Héber + Douglas | Planejar **Teresina - PI → Parnaíba - PI** com autonomia de ~195 km (a parada cai a 82% da autonomia, perto dos ~160 km até Piripiri; ajuste alguns km se o marcador não cair na cidade) e clicar no marcador do posto em **Piripiri (BR-343)**: o pop-up mostra CNPJ, razão social, avaliação, tempo de autorização ANP e combustíveis. |
| 05 | `05-dialogo-multilingue-gemini.png` | Héber + Douglas | Trocar o idioma no cabeçalho (ex.: English ou 中文) e pedir no chat um roteiro para **Piripiri - PI** citando o "Parque Nacional de Sete Cidades": a resposta vem no idioma escolhido com o nome do patrimônio preservado. |
| 06 | `06-roteiro-entregue-multicanal.png` | Héber | Enviar o roteiro pelo modal de despacho (E-mail ou WhatsApp) e capturar a mensagem recebida. |
| 07 | `07-logs-fastapi-backgroundtasks.png` | Mikaelle | Terminal do `uvicorn` mostrando linhas `[BackgroundTasks]` (DLQ, despacho ou evento de clima do WF 4) após um planejamento ou `/testardlq`. |

> Os postos ANP do catálogo local são uma **amostra ilustrativa** (CNPJs e razões sociais fictícios), usada quando o OpenStreetMap
> não confirma um posto real. Deixe isso claro na apresentação do print 04.

## Teste rápido do WF 4 (Clima + Gemini)

Com o n8n rodando e o WF 4 ativo:

```bash
curl -X POST http://localhost:5678/webhook/turismo-clima \
  -H "Content-Type: application/json" \
  -d '{"destino": "Piripiri - PI", "latitude": -4.2733, "longitude": -41.7769, "idioma": "en", "dias": 3}'
```

A resposta traz `nivel` (`verde`, `amarelo` ou `vermelho`), `alertas`, a `previsao` diária e as `orientacoes`
(`fonte_orientacoes` indica se vieram do Gemini ou da contingência).
