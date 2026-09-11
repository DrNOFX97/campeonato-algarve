-- ============================================================
-- Views e trigger de sincronização — Campeonato do Algarve
-- Não depende de haver jornadas/jogos/golos já inseridos.
-- ============================================================

-- ============================================================
-- VIEW 1: jogos e resultados
-- ============================================================
CREATE OR REPLACE VIEW view_jogos_resultados AS
SELECT
    j.id_jogo,
    jn.epoca,
    jn.numero              AS jornada,
    j.data_jogo,
    ce.nome                 AS equipa_casa,
    cv.nome                 AS equipa_visitante,
    e.nome                  AS estadio,
    j.golos_casa,
    j.golos_visitante,
    CASE
        WHEN j.golos_casa > j.golos_visitante THEN ce.nome
        WHEN j.golos_visitante > j.golos_casa THEN cv.nome
        ELSE 'Empate'
    END                      AS resultado
FROM jogo j
JOIN jornada jn ON jn.id_jornada = j.id_jornada
JOIN clube ce   ON ce.id_clube = j.id_equipa_casa
JOIN clube cv   ON cv.id_clube = j.id_equipa_visitante
JOIN estadio e  ON e.id_estadio = j.id_estadio;

-- ============================================================
-- VIEW 2: jogadores e clubes
-- ============================================================
CREATE OR REPLACE VIEW view_jogadores_clubes AS
SELECT
    jg.id_jogador,
    jg.nome              AS jogador,
    jg.data_nascimento,
    jg.nacionalidade,
    jg.posicao,
    jg.numero_camisola,
    c.id_clube,
    c.nome               AS clube,
    c.cidade             AS cidade_clube,
    c.ano_fundacao,
    e.nome               AS estadio
FROM jogador jg
JOIN clube c   ON c.id_clube = jg.id_clube
JOIN estadio e ON e.id_estadio = c.id_estadio;

-- ============================================================
-- Sincronização golo -> jogo (golos_casa / golos_visitante)
-- A tabela golo é a fonte da verdade; os campos golos_casa/
-- golos_visitante em jogo são um cache recalculado sempre que
-- golo muda (insert/update/delete).
-- ============================================================
CREATE OR REPLACE FUNCTION recalcular_resultado_jogo(p_id_jogo INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE jogo j
    SET golos_casa = (
            SELECT COUNT(*)
            FROM golo g
            JOIN jogador jg ON jg.id_jogador = g.id_jogador
            WHERE g.id_jogo = p_id_jogo
              AND jg.id_clube = j.id_equipa_casa
        ),
        golos_visitante = (
            SELECT COUNT(*)
            FROM golo g
            JOIN jogador jg ON jg.id_jogador = g.id_jogador
            WHERE g.id_jogo = p_id_jogo
              AND jg.id_clube = j.id_equipa_visitante
        )
    WHERE j.id_jogo = p_id_jogo;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION trg_sync_resultado_jogo() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        PERFORM recalcular_resultado_jogo(OLD.id_jogo);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        PERFORM recalcular_resultado_jogo(NEW.id_jogo);
        IF OLD.id_jogo IS DISTINCT FROM NEW.id_jogo THEN
            PERFORM recalcular_resultado_jogo(OLD.id_jogo);
        END IF;
        RETURN NEW;
    ELSE -- INSERT
        PERFORM recalcular_resultado_jogo(NEW.id_jogo);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS sync_resultado_jogo ON golo;
CREATE TRIGGER sync_resultado_jogo
AFTER INSERT OR UPDATE OR DELETE ON golo
FOR EACH ROW
EXECUTE FUNCTION trg_sync_resultado_jogo();

-- ============================================================
-- Bónus: total de golos por jogador (mencionado nos próximos
-- passos do projeto — não pedido agora, mas pequeno e útil)
-- ============================================================
CREATE OR REPLACE FUNCTION total_golos_jogador(p_id_jogador INTEGER)
RETURNS INTEGER AS $$
    SELECT COUNT(*)::INTEGER FROM golo WHERE id_jogador = p_id_jogador;
$$ LANGUAGE sql STABLE;
