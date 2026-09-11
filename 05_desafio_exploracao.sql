-- ============================================================
-- Desafio de exploração — Campeonato do Algarve
-- 5 queries que respondem às perguntas do enunciado.
-- Os valores de exemplo (jornada 1, id_jogo 91, "Sporting Clube
-- Farense") podem ser trocados por outros — são só para demonstrar
-- a query a correr sobre dados reais já inseridos.
-- ============================================================

-- 1. Que jogos foram realizados numa determinada jornada?
SELECT
    jn.numero          AS jornada,
    cc.nome             AS equipa_casa,
    jg.golos_casa,
    jg.golos_visitante,
    cv.nome             AS equipa_visitante,
    jg.data_jogo,
    e.nome              AS estadio
FROM jogo jg
JOIN jornada jn ON jn.id_jornada = jg.id_jornada
JOIN clube cc   ON cc.id_clube = jg.id_equipa_casa
JOIN clube cv   ON cv.id_clube = jg.id_equipa_visitante
JOIN estadio e  ON e.id_estadio = jg.id_estadio
WHERE jn.numero = 1
ORDER BY jg.id_jogo;

-- 2. Que jogadores pertencem a um determinado clube?
SELECT
    j.nome,
    j.posicao,
    j.numero_camisola,
    j.nacionalidade
FROM jogador j
JOIN clube c ON c.id_clube = j.id_clube
WHERE c.nome = 'Sporting Clube Farense'
ORDER BY j.numero_camisola;

-- 3. Quantos golos marcou cada jogador?
-- (inclui jogadores com 0 golos, via LEFT JOIN + COALESCE)
SELECT
    j.nome,
    c.nome                          AS clube,
    COALESCE(COUNT(g.id_golo), 0)   AS total_golos
FROM jogador j
JOIN clube c        ON c.id_clube = j.id_clube
LEFT JOIN golo g    ON g.id_jogador = j.id_jogador
GROUP BY j.id_jogador, j.nome, c.nome
ORDER BY total_golos DESC, j.nome;

-- 4. Que jogadores receberam cartões num determinado jogo?
SELECT
    j.nome,
    cl.nome        AS clube,
    c.tipo_cartao,
    c.minuto
FROM cartao c
JOIN jogador j ON j.id_jogador = c.id_jogador
JOIN clube cl  ON cl.id_clube = j.id_clube
WHERE c.id_jogo = 91
ORDER BY c.minuto;

-- 5. Qual foi o resultado de cada jogo realizado?
SELECT
    jn.numero      AS jornada,
    cc.nome         AS equipa_casa,
    jg.golos_casa,
    jg.golos_visitante,
    cv.nome         AS equipa_visitante,
    jg.data_jogo
FROM jogo jg
JOIN jornada jn ON jn.id_jornada = jg.id_jornada
JOIN clube cc   ON cc.id_clube = jg.id_equipa_casa
JOIN clube cv   ON cv.id_clube = jg.id_equipa_visitante
WHERE jg.jogado = TRUE
ORDER BY jn.numero, jg.id_jogo;
