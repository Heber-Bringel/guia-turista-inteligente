# Design System

## Direction

Interface de produto clara e responsiva para uso em trânsito ou durante o planejamento em casa. O tema é claro, com superfícies brancas e neutros azulados; o azul da versão Flask é preservado como cor de ação.

## Color

Os tokens usam OKLCH. Azul identifica ações e seleção; verde confirma; âmbar alerta; vermelho comunica erro ou exclusão. Estados nunca dependem apenas da cor.

## Typography

Plus Jakarta Sans, com fallback para a pilha do sistema. Escala compacta de produto, peso 700 para títulos e 600 para rótulos e controles. Textos explicativos têm largura máxima de 70 caracteres.

## Layout

Barra superior persistente, conteúdo central de até 1440 px e fluxo principal em duas colunas no desktop. No celular, formulário, resultado e histórico viram uma única coluna. Espaçamento segue múltiplos de 4 px.

## Components

Controles têm 44 px ou mais, raio de 10 px e foco visível. Painéis usam borda sutil ou sombra curta, nunca ambos como decoração. Skeletons preservam a estrutura durante carregamento; estados vazios ensinam a próxima ação.

## Motion

Transições de estado entre 150 e 220 ms. Movimento comunica carregamento, expansão ou confirmação e é removido quando `prefers-reduced-motion` estiver ativo.
