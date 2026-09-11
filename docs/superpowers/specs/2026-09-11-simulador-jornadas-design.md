# Simulador de Jornadas — Campeonato do Algarve

**Data:** 2026-09-11
**Estado:** aprovado em conversa, a aguardar revisão desta spec

## Contexto

O "Projeto final SQL - Futebol" tem a base de dados `campeonato` já populada
com dados reais (6 clubes, 6 estádios, 6 treinadores, 161 jogadores,
extraídos do zerozero.pt) e as views `view_jogos_resultados` /
`view_jogadores_clubes` + o trigger `sync_resultado_jogo` já criados
(ver `01_campeonato_futebol_schema.sql` e `04_views_e_trigger.sql`).

Falta ainda popular `jornada`, `jogo`, `golo`, `cartao` — dados
explicitamente fictícios (não devem ser atribuídos como factos reais a
clubes/jogadores verdadeiros). Em vez de um script que insere valores
fixos, o dono do projeto quer uma pequena aplicação web, ao estilo
Football Manager: um botão "simular jornada" que gera um jogo aleatório
de cada vez, para tornar esta parte do projeto mais divertida de usar e
demonstrar.

## Objetivo

Construir uma mini-aplicação local (Flask + HTML/CSS/JS simples) que:
1. Gera o calendário da época (5 jornadas, 15 jogos, todos os 6 clubes
   contra todos, uma vez).
2. Permite simular uma jornada de cada vez, gerando golos (com
   marcador e minuto) e cartões de forma aleatória mas
   estatisticamente plausível, e guardando tudo na base de dados.
3. Mostra os resultados e uma tabela classificativa calculada em SQL.

## Fora de âmbito

- Autenticação/utilizadores — aplicação local, uso pessoal.
- Deploy remoto — corre localmente (`python app.py`) contra o Postgres
  local já em uso.
- Dupla volta, playoffs, ou qualquer estrutura de época além de volta
  única — decidido explicitamente que não.
- Edição manual de resultados pela UI — só simulação aleatória.

## Arquitetura

- **Backend:** Flask (Python) + `psycopg2`, um único processo local.
  Serve tanto a API JSON como os ficheiros estáticos (`static/index.html`,
  `static/style.css`, `static/app.js`) — sem build step, sem servidor
  separado.
- **Frontend:** uma página HTML, CSS simples, JS puro (`fetch` para a
  API, sem framework).
- **Base de dados:** `campeonato` (Postgres local, já existente). A
  app não altera o schema — só insere linhas em `jornada`, `jogo`,
  `golo`, `cartao`. O trigger `sync_resultado_jogo` já existente
  mantém `jogo.golos_casa`/`golos_visitante` sincronizados sempre que
  se insere em `golo` — a app nunca escreve esses campos diretamente.

## Geração do calendário

Algoritmo round-robin clássico ("circle method") para 6 equipas:
- Fixa uma equipa, roda as outras 5 à volta dela em cada jornada →
  5 jornadas, 3 confrontos por jornada, cada equipa joga com todas as
  outras exatamente uma vez.
- Casa/fora: alternado por confronto (para não ficar sempre a mesma
  equipa em casa em todas as jornadas em que aparece).
- `jornada.epoca` = `'2026/2027'` (fictício, mesma convenção usada no
  futebol real).
- `jogo.data_jogo`: sequencial, uma jornada por semana, a partir de
  `2026-09-20` (domingo, data fixa e arbitrária), +7 dias por jornada —
  só para preencher o campo `NOT NULL`, sem significado real.
- `jogo.id_estadio` = estádio do clube da casa (`clube.id_estadio`).
- `jogo.golos_casa` / `golos_visitante` ficam a `0` (default do
  schema) até a jornada ser simulada.

Endpoint: `POST /calendario/gerar` — só pode ser chamado uma vez (falha
com erro claro se `jornada` já tiver linhas); insere as 5 jornadas e os
15 jogos numa única transação.

## Simulação de uma jornada

Endpoint: `POST /jornadas/<numero>/simular`

Para cada um dos 3 jogos dessa jornada (falha se a jornada já tiver
sido simulada, ou se não existir):

1. **Golos por equipa:** `n = numpy.random.poisson(1.3)` — sem
   dependência de `numpy` só para isto; usar a implementação do
   algoritmo de Knuth para amostragem Poisson em Python puro (poucas
   linhas), para não obrigar a instalar `numpy`.
2. **Marcador de cada golo:** escolhido por peso de posição dentro do
   plantel dessa equipa, via `random.choices(jogadores, weights=...)`:
   - Avançado, Ponta de Lança, Extremo Esquerdo/Direito → peso 4
   - Médio Ofensivo, Médio Centro, Médio, Médio Direito → peso 2
   - Médio Defensivo → peso 1
   - Defesa, Defesa Central/Direito/Esquerdo → peso 0.5
   - Guarda Redes → peso 0.05
   (classificação por correspondência de substring no valor de
   `jogador.posicao`, não por tabela exaustiva — cobre variações
   futuras sem precisar de manutenção)
   - Minuto: `random.randint(1, 90)`
3. **Cartões:** por cada jogador que participou no jogo (aproximação:
   todo o plantel considerado "em campo" — não há tabela de
   titulares/suplentes no schema), probabilidade independente:
   - 8% de cartão amarelo
   - 0.5% de cartão vermelho (não combinado com amarelo, para
     simplificar — um jogador tem no máximo 1 cartão por jogo nesta
     simulação)
   - Minuto: `random.randint(1, 90)`
4. Insere as linhas resultantes em `golo` e `cartao`. **Não** escreve
   em `jogo.golos_casa`/`golos_visitante` — o trigger trata disso.
5. Devolve JSON com o resultado dos 3 jogos (equipas, golos, marcadores
   e minutos, cartões) para o frontend mostrar.

Tudo dentro de uma transação por jornada (ou os 3 jogos simulam todos,
ou nenhum, em caso de erro a meio).

## Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/classificacao` | Tabela classificativa calculada em SQL (pontos, V/E/D, golos marcados/sofridos) a partir de `view_jogos_resultados` |
| GET | `/api/jornadas` | Lista as 5 jornadas com estado (por jogar / já simulada) e os respetivos jogos |
| POST | `/api/calendario/gerar` | Gera as 5 jornadas + 15 jogos (uma vez só) |
| POST | `/api/jornadas/<numero>/simular` | Simula os 3 jogos dessa jornada |
| POST | `/api/epoca/reiniciar` | Apaga `cartao`, `golo`, `jogo`, `jornada` (nessa ordem, por causa das FKs) — para testar a simulação de novo do zero |

## Frontend

Uma única página (`index.html`):
- **Topo:** tabela classificativa (atualiza depois de cada simulação).
- **Lista de jornadas 1-5:** cada uma mostra os 3 confrontos.
  - Jornada por jogar: botão "▶ Simular Jornada N".
  - Jornada já simulada: mostra o resultado de cada jogo (sem botão).
- **Botão "Gerar Calendário"** visível só se ainda não houver jornadas.
- **Botão "Reiniciar Época"** sempre visível, com confirmação
  (`confirm()` do browser) antes de chamar o endpoint — apaga tudo e
  volta ao estado inicial.
- Sem qualquer amostragem de golos/cartões faltar — se uma jornada dá
  erro a simular, mostra a mensagem de erro e não mexe no estado.

## Tratamento de erros

- Backend valida sempre: jornada existe? já foi simulada? calendário já
  foi gerado (no caso do `/calendario/gerar`)? Erros devolvem HTTP 400
  com mensagem clara em JSON (`{"erro": "..."}`), que o frontend mostra
  num banner.
- Todas as operações de escrita (gerar calendário, simular jornada,
  reiniciar) correm dentro de uma transação — falha a meio não deixa
  dados parciais.

## Testes

- Teste manual: gerar calendário → simular as 5 jornadas uma a uma →
  confirmar que a tabela classificativa fecha com 15 jogos e que a
  soma de pontos/jogos bate certo (cada equipa jogou 5).
- Teste manual do trigger: inserir/apagar uma linha em `golo`
  diretamente via `psql` e confirmar que `jogo.golos_casa`/
  `golos_visitante` mudam sem intervenção da app (já coberto pelo
  trigger existente, mas vale confirmar aqui que a app não duplica essa
  lógica).
- Sem testes automatizados formais — âmbito académico, verificação
  manual é suficiente.
