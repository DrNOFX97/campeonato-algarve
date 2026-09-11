"""
Gera 02_dados_teste.sql a partir de clubes_algarve.json.

Popula: estadio, clube, treinador, jogador (jornada/jogo/golo/cartao ficam
fictícios e são criados à parte, fora deste gerador).

Uso:
    python gerar_inserts.py
"""

import json

ENTRADA = "clubes_algarve.json"
SAIDA = "02_dados_teste.sql"


def sql_str(valor) -> str:
    if valor is None:
        return "NULL"
    escapado = str(valor).replace("'", "''")
    return f"'{escapado}'"


def sql_int(valor) -> str:
    return "NULL" if valor is None else str(int(valor))


def main() -> None:
    with open(ENTRADA, encoding="utf-8") as f:
        clubes = json.load(f)

    linhas = [
        "-- ============================================================",
        "-- Dados de teste — Campeonato do Algarve",
        "-- Gerado automaticamente a partir de clubes_algarve.json (zerozero.pt)",
        "-- ============================================================",
        "",
        "-- 1. ESTADIO",
        "INSERT INTO estadio (nome, cidade, capacidade) VALUES",
    ]

    valores_estadio = [
        f"({sql_str(r['estadio']['nome'])}, {sql_str(r['estadio']['cidade'])}, {sql_int(r['estadio']['capacidade'])})"
        for r in clubes
    ]
    linhas.append(",\n".join(valores_estadio) + ";")
    linhas.append("")

    linhas.append("-- 2. CLUBE")
    linhas.append("INSERT INTO clube (nome, cidade, ano_fundacao, id_estadio) VALUES")
    valores_clube = []
    for r in clubes:
        c = r["clube"]
        subquery_estadio = f"(SELECT id_estadio FROM estadio WHERE nome = {sql_str(r['estadio']['nome'])})"
        valores_clube.append(
            f"({sql_str(c['nome'])}, {sql_str(c['cidade'])}, {sql_int(c['ano_fundacao'])}, {subquery_estadio})"
        )
    linhas.append(",\n".join(valores_clube) + ";")
    linhas.append("")

    linhas.append("-- 3. TREINADOR")
    linhas.append("INSERT INTO treinador (nome, id_clube) VALUES")
    valores_treinador = []
    for r in clubes:
        if not r["treinador"]["nome"]:
            continue
        subquery_clube = f"(SELECT id_clube FROM clube WHERE nome = {sql_str(r['clube']['nome'])})"
        valores_treinador.append(f"({sql_str(r['treinador']['nome'])}, {subquery_clube})")
    linhas.append(",\n".join(valores_treinador) + ";")
    linhas.append("")

    linhas.append("-- 4. JOGADOR")
    linhas.append("INSERT INTO jogador (nome, data_nascimento, nacionalidade, posicao, numero_camisola, id_clube) VALUES")
    valores_jogador = []
    total_jogadores = 0
    for r in clubes:
        subquery_clube = f"(SELECT id_clube FROM clube WHERE nome = {sql_str(r['clube']['nome'])})"
        for j in r["jogadores"]:
            if j["numero_camisola"] is None:
                continue  # excluídos: numero_camisola é NOT NULL no schema
            total_jogadores += 1
            valores_jogador.append(
                "("
                f"{sql_str(j['nome'])}, "
                f"{sql_str(j['data_nascimento'])}, "
                f"{sql_str(j['nacionalidade'])}, "
                f"{sql_str(j['posicao'])}, "
                f"{sql_int(j['numero_camisola'])}, "
                f"{subquery_clube}"
                ")"
            )
    linhas.append(",\n".join(valores_jogador) + ";")
    linhas.append("")

    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    print(f"Escrito {SAIDA}: {len(clubes)} estádios, {len(clubes)} clubes, "
          f"{len(valores_treinador)} treinadores, {total_jogadores} jogadores.")


if __name__ == "__main__":
    main()
