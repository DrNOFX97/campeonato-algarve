"""
Simulador de jornadas — Campeonato do Algarve.

Backend Flask que serve a API (calendário, simulação, classificação) e o
frontend estático (static/). Ver docs/superpowers/specs/2026-09-11-simulador-jornadas-design.md.
"""

import math
import os
import random
from datetime import date, timedelta

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__, static_folder="static", static_url_path="")

DB_DSN = os.environ.get("CAMPEONATO_DSN", "host=localhost dbname=campeonato user=postgres")

EPOCA = "2026/2027"
DATA_INICIAL = date(2026, 9, 20)
MEDIA_GOLOS = 1.3
PROB_AMARELO = 0.08
PROB_VERMELHO = 0.005


def get_conn():
    return psycopg2.connect(DB_DSN)


def erro(mensagem, codigo=400):
    return jsonify({"erro": mensagem}), codigo


# ------------------------------------------------------------------
# Simulação: golos e cartões
# ------------------------------------------------------------------

def poisson_amostra(lam: float) -> int:
    """Amostra de uma distribuição Poisson (algoritmo de Knuth, sem numpy)."""
    limite = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= limite:
            return k - 1


def peso_posicao(posicao: str) -> float:
    """Peso de probabilidade de marcar, por posição (maior = mais provável)."""
    p = (posicao or "").lower()
    if "guarda" in p:
        return 0.05
    if "defensivo" in p:
        return 1
    if "defesa" in p:
        return 0.5
    if "avan" in p or "extremo" in p or "ponta de lan" in p:
        return 4
    if "dio" in p:  # médio, médio centro, médio ofensivo...
        return 2
    return 1


def simular_jogo(cur, id_jogo, plantel_casa, plantel_visitante):
    golos_casa = poisson_amostra(MEDIA_GOLOS)
    golos_visitante = poisson_amostra(MEDIA_GOLOS)

    resultado = {"golos": [], "cartoes": []}

    for lado, plantel, n_golos in (
        ("casa", plantel_casa, golos_casa),
        ("visitante", plantel_visitante, golos_visitante),
    ):
        if not plantel:
            continue
        pesos = [peso_posicao(j["posicao"]) for j in plantel]
        for _ in range(n_golos):
            marcador = random.choices(plantel, weights=pesos, k=1)[0]
            minuto = random.randint(1, 90)
            cur.execute(
                "INSERT INTO golo (id_jogador, id_jogo, minuto) VALUES (%s, %s, %s)",
                (marcador["id_jogador"], id_jogo, minuto),
            )
            resultado["golos"].append(
                {"lado": lado, "jogador": marcador["nome"], "minuto": minuto}
            )

    for lado, plantel in (("casa", plantel_casa), ("visitante", plantel_visitante)):
        for jogador in plantel:
            r = random.random()
            if r < PROB_VERMELHO:
                tipo = "Vermelho"
            elif r < PROB_VERMELHO + PROB_AMARELO:
                tipo = "Amarelo"
            else:
                continue
            minuto = random.randint(1, 90)
            cur.execute(
                "INSERT INTO cartao (id_jogador, id_jogo, minuto, tipo_cartao) VALUES (%s, %s, %s, %s)",
                (jogador["id_jogador"], id_jogo, minuto, tipo),
            )
            resultado["cartoes"].append(
                {"lado": lado, "jogador": jogador["nome"], "minuto": minuto, "tipo": tipo}
            )

    cur.execute("UPDATE jogo SET jogado = TRUE WHERE id_jogo = %s", (id_jogo,))
    return resultado


# ------------------------------------------------------------------
# Calendário: round-robin (circle method)
# ------------------------------------------------------------------

def gerar_confrontos_round_robin(ids_clubes):
    times = list(ids_clubes)
    n = len(times)
    fixo = times[0]
    rotativos = times[1:]
    jornadas = []
    for rodada in range(n - 1):
        ordem = [fixo] + rotativos
        confrontos = []
        for i in range(n // 2):
            a, b = ordem[i], ordem[n - 1 - i]
            confrontos.append((a, b) if rodada % 2 == 0 else (b, a))
        jornadas.append(confrontos)
        rotativos = [rotativos[-1]] + rotativos[:-1]
    return jornadas


# ------------------------------------------------------------------
# Rotas: frontend estático
# ------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ------------------------------------------------------------------
# API: classificação
# ------------------------------------------------------------------

@app.route("/api/classificacao")
def classificacao():
    sql = """
    WITH linhas AS (
        SELECT id_equipa_casa AS id_clube, golos_casa AS marcados, golos_visitante AS sofridos
        FROM jogo WHERE jogado = TRUE
        UNION ALL
        SELECT id_equipa_visitante AS id_clube, golos_visitante AS marcados, golos_casa AS sofridos
        FROM jogo WHERE jogado = TRUE
    )
    SELECT
        c.id_clube, c.nome, c.logo_url,
        COUNT(l.id_clube) AS jogos,
        COUNT(*) FILTER (WHERE l.marcados > l.sofridos) AS vitorias,
        COUNT(*) FILTER (WHERE l.marcados = l.sofridos) AS empates,
        COUNT(*) FILTER (WHERE l.marcados < l.sofridos) AS derrotas,
        COALESCE(SUM(l.marcados), 0)::int AS golos_marcados,
        COALESCE(SUM(l.sofridos), 0)::int AS golos_sofridos,
        COALESCE(SUM(l.marcados) - SUM(l.sofridos), 0)::int AS diferenca,
        COALESCE(SUM(
            CASE WHEN l.marcados > l.sofridos THEN 3
                 WHEN l.marcados = l.sofridos THEN 1
                 ELSE 0 END
        ), 0)::int AS pontos
    FROM clube c
    LEFT JOIN linhas l ON l.id_clube = c.id_clube
    GROUP BY c.id_clube, c.nome, c.logo_url
    ORDER BY pontos DESC, diferenca DESC, golos_marcados DESC, c.nome ASC;
    """
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        linhas = cur.fetchall()
    return jsonify(linhas)


# ------------------------------------------------------------------
# API: jornadas (lista + jogos de cada uma)
# ------------------------------------------------------------------

@app.route("/api/jornadas")
def listar_jornadas():
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id_jornada, numero, epoca FROM jornada ORDER BY numero")
        jornadas = cur.fetchall()
        if not jornadas:
            return jsonify([])

        cur.execute(
            """
            SELECT jg.id_jogo, jg.id_jornada, jg.data_jogo, jg.golos_casa, jg.golos_visitante, jg.jogado,
                   cc.id_clube AS id_casa, cc.nome AS casa, cc.logo_url AS casa_logo,
                   cv.id_clube AS id_visitante, cv.nome AS visitante, cv.logo_url AS visitante_logo,
                   e.nome AS estadio
            FROM jogo jg
            JOIN clube cc ON cc.id_clube = jg.id_equipa_casa
            JOIN clube cv ON cv.id_clube = jg.id_equipa_visitante
            JOIN estadio e ON e.id_estadio = jg.id_estadio
            ORDER BY jg.id_jornada, jg.id_jogo
            """
        )
        jogos = cur.fetchall()

        ids_jogados = [j["id_jogo"] for j in jogos if j["jogado"]]
        golos_por_jogo, cartoes_por_jogo = {}, {}
        if ids_jogados:
            cur.execute(
                """
                SELECT g.id_jogo, jg.nome AS jogador, jg.id_clube, g.minuto
                FROM golo g JOIN jogador jg ON jg.id_jogador = g.id_jogador
                WHERE g.id_jogo = ANY(%s) ORDER BY g.minuto
                """,
                (ids_jogados,),
            )
            for row in cur.fetchall():
                golos_por_jogo.setdefault(row["id_jogo"], []).append(row)

            cur.execute(
                """
                SELECT c.id_jogo, jg.nome AS jogador, jg.id_clube, c.minuto, c.tipo_cartao
                FROM cartao c JOIN jogador jg ON jg.id_jogador = c.id_jogador
                WHERE c.id_jogo = ANY(%s) ORDER BY c.minuto
                """,
                (ids_jogados,),
            )
            for row in cur.fetchall():
                cartoes_por_jogo.setdefault(row["id_jogo"], []).append(row)

    por_jornada = {j["id_jornada"]: dict(j, jogos=[]) for j in jornadas}
    for jg in jogos:
        jg = dict(jg)
        jg["golos"] = golos_por_jogo.get(jg["id_jogo"], [])
        jg["cartoes"] = cartoes_por_jogo.get(jg["id_jogo"], [])
        por_jornada[jg["id_jornada"]]["jogos"].append(jg)

    return jsonify(list(por_jornada.values()))


# ------------------------------------------------------------------
# API: gerar calendário
# ------------------------------------------------------------------

@app.route("/api/calendario/gerar", methods=["POST"])
def gerar_calendario():
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT COUNT(*) AS n FROM jornada")
        if cur.fetchone()["n"] > 0:
            return erro("O calendário já foi gerado. Reinicia a época primeiro se quiseres gerar de novo.")

        cur.execute("SELECT id_clube, id_estadio FROM clube ORDER BY id_clube")
        clubes = cur.fetchall()
        if len(clubes) < 2:
            return erro("Não há clubes suficientes na base de dados.", 500)

        estadio_por_clube = {c["id_clube"]: c["id_estadio"] for c in clubes}
        ids_clubes = [c["id_clube"] for c in clubes]
        rodadas = gerar_confrontos_round_robin(ids_clubes)

        for indice, confrontos in enumerate(rodadas):
            numero = indice + 1
            data_jornada = DATA_INICIAL + timedelta(weeks=indice)
            cur.execute(
                "INSERT INTO jornada (numero, epoca) VALUES (%s, %s) RETURNING id_jornada",
                (numero, EPOCA),
            )
            id_jornada = cur.fetchone()["id_jornada"]
            for id_casa, id_visitante in confrontos:
                cur.execute(
                    """
                    INSERT INTO jogo (id_jornada, data_jogo, id_equipa_casa, id_equipa_visitante, id_estadio)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (id_jornada, data_jornada, id_casa, id_visitante, estadio_por_clube[id_casa]),
                )
        conn.commit()

    return jsonify({"ok": True, "jornadas": len(rodadas)})


# ------------------------------------------------------------------
# API: simular jornada
# ------------------------------------------------------------------

@app.route("/api/jornadas/<int:numero>/simular", methods=["POST"])
def simular_jornada(numero):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id_jornada FROM jornada WHERE numero = %s AND epoca = %s", (numero, EPOCA))
        row = cur.fetchone()
        if not row:
            return erro(f"A jornada {numero} não existe.", 404)
        id_jornada = row["id_jornada"]

        cur.execute(
            """
            SELECT id_jogo, id_equipa_casa, id_equipa_visitante,
                   cc.nome AS casa, cv.nome AS visitante, jogado
            FROM jogo jg
            JOIN clube cc ON cc.id_clube = jg.id_equipa_casa
            JOIN clube cv ON cv.id_clube = jg.id_equipa_visitante
            WHERE id_jornada = %s
            ORDER BY id_jogo
            """,
            (id_jornada,),
        )
        jogos = cur.fetchall()
        if not jogos:
            return erro(f"A jornada {numero} não tem jogos.", 404)
        if any(j["jogado"] for j in jogos):
            return erro(f"A jornada {numero} já foi simulada.")

        resultados = []
        for jogo in jogos:
            cur.execute(
                "SELECT id_jogador, nome, posicao FROM jogador WHERE id_clube = %s",
                (jogo["id_equipa_casa"],),
            )
            plantel_casa = cur.fetchall()
            cur.execute(
                "SELECT id_jogador, nome, posicao FROM jogador WHERE id_clube = %s",
                (jogo["id_equipa_visitante"],),
            )
            plantel_visitante = cur.fetchall()

            detalhe = simular_jogo(cur, jogo["id_jogo"], plantel_casa, plantel_visitante)
            resultados.append(
                {
                    "id_jogo": jogo["id_jogo"],
                    "casa": jogo["casa"],
                    "visitante": jogo["visitante"],
                    **detalhe,
                }
            )

        # golos_casa/golos_visitante já foram atualizados pelo trigger sync_resultado_jogo
        cur.execute(
            "SELECT id_jogo, golos_casa, golos_visitante FROM jogo WHERE id_jornada = %s",
            (id_jornada,),
        )
        placares = {r["id_jogo"]: r for r in cur.fetchall()}
        for r in resultados:
            r["golos_casa"] = placares[r["id_jogo"]]["golos_casa"]
            r["golos_visitante"] = placares[r["id_jogo"]]["golos_visitante"]

        conn.commit()

    return jsonify({"ok": True, "numero": numero, "jogos": resultados})


# ------------------------------------------------------------------
# API: reiniciar época
# ------------------------------------------------------------------

@app.route("/api/epoca/reiniciar", methods=["POST"])
def reiniciar_epoca():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM cartao")
        cur.execute("DELETE FROM golo")
        cur.execute("DELETE FROM jogo")
        cur.execute("DELETE FROM jornada")
        conn.commit()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
