"""
Vai buscar só o logo de cada clube (sem re-raspar plantel/treinador) e
atualiza clubes_algarve.json + gera 03_atualizar_logos.sql.
"""

import json
import random
import time

import requests
from bs4 import BeautifulSoup

from scrape_clubes_algarve import CLUBES, USER_AGENT, MIN_DELAY, MAX_DELAY, TIMEOUT, extrair_logo  # type: ignore

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "pt-PT,pt;q=0.9"})


def sql_str_local(valor):
    if valor is None:
        return "NULL"
    return "'" + str(valor).replace("'", "''") + "'"


def main():
    with open("clubes_algarve.json", encoding="utf-8") as f:
        data = json.load(f)

    # Chave pelo URL, não pelo nome — nome_config (rótulo de configuração)
    # pode diferir do nome oficial extraído do "Dados Gerais" (ex.: Ferreiras).
    logos_por_url = {}
    for config in CLUBES:
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        resp = session.get(config["url"], timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        logo_url = extrair_logo(soup)
        logos_por_url[config["url"]] = logo_url
        print(f"{config['nome_config']}: {logo_url}")

    for r, config in zip(data, CLUBES):
        r["clube"]["logo_url"] = logos_por_url.get(config["url"])

    with open("clubes_algarve.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    linhas = ["-- Atualização: logo_url dos clubes", ""]
    for r in data:
        linhas.append(
            f"UPDATE clube SET logo_url = {sql_str_local(r['clube']['logo_url'])} "
            f"WHERE nome = {sql_str_local(r['clube']['nome'])};"
        )
    with open("03_atualizar_logos.sql", "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    print("\nEscrito 03_atualizar_logos.sql")


if __name__ == "__main__":
    main()
