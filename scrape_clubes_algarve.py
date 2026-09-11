"""
Scraper de clubes de futebol do Algarve (zerozero.pt) para o projeto académico
"Projeto final SQL - Futebol" (Campeonato do Algarve).

Recolhe, por clube: estádio (nome/cidade/capacidade), dados do clube
(nome/cidade/ano de fundação), treinador principal e plantel (nome, data de
nascimento, nacionalidade, posição, número de camisola).

Uso:
    python scrape_clubes_algarve.py

Saída:
    clubes_algarve.json
"""

import json
import logging
import random
import re
import time
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.zerozero.pt"
USER_AGENT = "CampeonatoAlgarveSQL-EducationalScraper/1.0 (projeto academico CET, uso nao comercial)"
MIN_DELAY = 1.0
MAX_DELAY = 2.0
TIMEOUT = 20

CLUBES = [
    {"nome_config": "Sporting Clube Farense", "url": f"{BASE_URL}/equipa/farense/10"},
    {"nome_config": "Louletano Desportos Clube", "url": f"{BASE_URL}/equipa/louletano/3596"},
    {"nome_config": "Imortal Desportivo Clube", "url": f"{BASE_URL}/equipa/imortal-dc/1174"},
    {"nome_config": "Portimonense Sporting Clube", "url": f"{BASE_URL}/equipa/portimonense/33"},
    {"nome_config": "Sporting Clube Olhanense", "url": f"{BASE_URL}/equipa/olhanense/2172"},
    {"nome_config": "Sporting Clube Ferreiras", "url": f"{BASE_URL}/equipa/ferreiras/6301"},
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("zerozero_algarve")

session = requests.Session()
session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept-Language": "pt-PT,pt;q=0.9",
})


def get_soup(url: str) -> Optional[BeautifulSoup]:
    """GET com rate limiting (1-2s) e falha graciosa (devolve None)."""
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    try:
        resp = session.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Falha ao obter %s: %s", url, exc)
        return None
    return BeautifulSoup(resp.text, "html.parser")


def _card_by_heading(soup: BeautifulSoup, heading_text: str, case_sensitive: bool = True):
    def matcher(s):
        if not s:
            return False
        return s.strip() == heading_text if case_sensitive else s.strip().lower() == heading_text.lower()

    header = soup.find("h2", string=matcher)
    if not header:
        return None
    return header.find_parent("div", class_="card-data")


def _rows_as_dict(card) -> dict:
    campos = {}
    for row in card.select(".card-data__row"):
        label = row.select_one(".card-data__label")
        value = row.select_one(".card-data__value, .card-data__values")
        if label and value:
            campos[label.get_text(strip=True)] = value
    return campos


def extrair_estadio(soup: BeautifulSoup) -> dict:
    resultado = {"nome": None, "cidade": None, "capacidade": None}
    stadium_div = soup.find(id="stadium")
    if not stadium_div:
        log.warning("Sem bloco de estádio na página")
        return resultado

    try:
        nome_el = stadium_div.select_one(".name a")
        resultado["nome"] = nome_el.get_text(strip=True) if nome_el else None
    except Exception:
        log.warning("Falha ao extrair nome do estádio", exc_info=True)

    try:
        cidade_el = stadium_div.select_one(".name .micrologo_and_text .text")
        resultado["cidade"] = cidade_el.get_text(strip=True) if cidade_el else None
    except Exception:
        log.warning("Falha ao extrair cidade do estádio", exc_info=True)

    try:
        for info in stadium_div.select(".information"):
            if info.get_text(strip=True).startswith("Lotação"):
                span = info.find("span")
                if span:
                    digitos = re.sub(r"[^\d]", "", span.get_text(strip=True))
                    resultado["capacidade"] = int(digitos) if digitos else None
                break
    except Exception:
        log.warning("Falha ao extrair capacidade do estádio", exc_info=True)

    return resultado


def extrair_logo(soup: BeautifulSoup) -> Optional[str]:
    logo_el = soup.select_one(".zz-enthdr-media .logo img")
    if logo_el and logo_el.get("src"):
        return logo_el["src"]
    log.warning("Logo do clube não encontrado")
    return None


def extrair_clube(soup: BeautifulSoup) -> dict:
    resultado = {"nome": None, "cidade": None, "ano_fundacao": None, "logo_url": None}
    resultado["logo_url"] = extrair_logo(soup)
    card = _card_by_heading(soup, "Dados Gerais")
    if not card:
        log.warning("Sem cartão 'Dados Gerais' para o clube")
        return resultado

    campos = _rows_as_dict(card)

    nome_el = campos.get("Nome")
    resultado["nome"] = nome_el.get_text(strip=True) if nome_el else None
    if not resultado["nome"]:
        log.warning("Nome do clube não encontrado")

    fundacao_el = campos.get("Ano de Fundação")
    if fundacao_el:
        match = re.match(r"(\d{4})", fundacao_el.get_text(strip=True))
        resultado["ano_fundacao"] = int(match.group(1)) if match else None
    else:
        log.warning("Ano de fundação não encontrado")

    cidade_el = campos.get("Cidade")
    resultado["cidade"] = cidade_el.get_text(strip=True) if cidade_el else None
    if not resultado["cidade"]:
        log.warning("Cidade do clube não encontrada")

    return resultado


def extrair_treinador(soup: BeautifulSoup) -> dict:
    header = soup.find("h2", string=lambda s: s and s.strip().lower() == "equipa técnica")
    if not header:
        log.warning("Sem cartão 'equipa técnica' — treinador não disponível")
        return {"nome": None}

    staff_card = header.find_parent("div", class_="card-data")
    for box in staff_card.select(".innerbox"):
        section = box.find("div", class_="section")
        if section and section.get_text(strip=True) == "Treinador":
            link = box.select_one(".staff .name .micrologo_and_text .text a")
            if link:
                return {"nome": link.get_text(strip=True)}
            break

    log.warning("Secção 'Treinador' não encontrada dentro de 'equipa técnica'")
    return {"nome": None}


def extrair_plantel_links(soup: BeautifulSoup) -> list:
    header = soup.find("h2", string=lambda s: s and s.strip().lower() == "plantel")
    if not header:
        log.warning("Sem plantel disponível nesta página")
        return []

    plantel_card = header.find_parent("div", class_="card-data")
    jogadores = []
    for staff in plantel_card.select(".staff_line .staff"):
        link = staff.select_one(".name .micrologo_and_text .text a")
        if not link or not link.get("href"):
            continue

        numero = None
        numero_el = staff.select_one(".number")
        if numero_el:
            digitos = re.sub(r"[^\d]", "", numero_el.get_text(strip=True))
            numero = int(digitos) if digitos else None

        jogadores.append({
            "numero_camisola": numero,
            "nome": link.get_text(strip=True),
            "url": urljoin(BASE_URL, link["href"].split("?")[0]),
        })
    return jogadores


def extrair_jogador_detalhe(soup: BeautifulSoup) -> dict:
    resultado = {"data_nascimento": None, "posicao": None, "nacionalidade": None}
    card = _card_by_heading(soup, "dados pessoais", case_sensitive=False)
    if not card:
        log.warning("Sem cartão 'Dados Pessoais' na página do jogador")
        return resultado

    campos = _rows_as_dict(card)

    nascimento_el = campos.get("Data de Nascimento")
    if nascimento_el:
        match = re.match(r"(\d{4}-\d{2}-\d{2})", nascimento_el.get_text(strip=True))
        resultado["data_nascimento"] = match.group(1) if match else None
    else:
        log.warning("Data de nascimento não encontrada")

    # Jogadores com posição secundária têm 2 spans .card-data__value seguidos
    # (ex.: "Defesa Central" + "Defesa Direito"); ficamos só com a primária.
    posicao_el = campos.get("Posição")
    if posicao_el:
        primeiro_valor = posicao_el.select_one(".card-data__value")
        resultado["posicao"] = (
            primeiro_valor.get_text(strip=True) if primeiro_valor else posicao_el.get_text(strip=True)
        )
    else:
        log.warning("Posição não encontrada")

    # Rótulo pode ser "Nacionalidade" ou "Nacionalidade / Dupla Nacionalidade"
    nac_el = next((v for k, v in campos.items() if k.startswith("Nacionalidade")), None)
    if nac_el:
        flag_link = nac_el.select_one("a[title]")
        resultado["nacionalidade"] = flag_link["title"] if flag_link else nac_el.get_text(strip=True)
    else:
        log.warning("Nacionalidade não encontrada")

    return resultado


def scrape_clube(config: dict) -> dict:
    nome_config = config["nome_config"]
    url = config["url"]
    log.info("=== %s (%s) ===", nome_config, url)

    vazio = {
        "estadio": {"nome": None, "cidade": None, "capacidade": None},
        "clube": {"nome": nome_config, "cidade": None, "ano_fundacao": None, "logo_url": None},
        "treinador": {"nome": None},
        "jogadores": [],
    }

    soup = get_soup(url)
    if soup is None:
        log.error("Não foi possível carregar a página de %s — clube com dados vazios", nome_config)
        return vazio

    try:
        estadio = extrair_estadio(soup)
    except Exception:
        log.warning("Erro inesperado a extrair estádio de %s", nome_config, exc_info=True)
        estadio = vazio["estadio"]

    try:
        clube = extrair_clube(soup)
    except Exception:
        log.warning("Erro inesperado a extrair dados do clube %s", nome_config, exc_info=True)
        clube = vazio["clube"]

    try:
        treinador = extrair_treinador(soup)
    except Exception:
        log.warning("Erro inesperado a extrair treinador de %s", nome_config, exc_info=True)
        treinador = {"nome": None}

    try:
        plantel_links = extrair_plantel_links(soup)
    except Exception:
        log.warning("Erro inesperado a extrair plantel de %s", nome_config, exc_info=True)
        plantel_links = []

    jogadores = []
    for entrada in plantel_links:
        log.info("  -> jogador: %s (#%s)", entrada["nome"], entrada["numero_camisola"])
        detalhe = {"data_nascimento": None, "posicao": None, "nacionalidade": None}
        try:
            soup_jogador = get_soup(entrada["url"])
            if soup_jogador is not None:
                detalhe = extrair_jogador_detalhe(soup_jogador)
            else:
                log.warning("  Falha ao carregar página do jogador %s", entrada["nome"])
        except Exception:
            log.warning("  Erro inesperado no jogador %s", entrada["nome"], exc_info=True)

        jogadores.append({
            "nome": entrada["nome"],
            "data_nascimento": detalhe["data_nascimento"],
            "nacionalidade": detalhe["nacionalidade"],
            "posicao": detalhe["posicao"],
            "numero_camisola": entrada["numero_camisola"],
        })

    return {
        "estadio": estadio,
        "clube": clube,
        "treinador": treinador,
        "jogadores": jogadores,
    }


def imprimir_resumo(resultados: list) -> None:
    print("\n" + "=" * 60)
    print("RESUMO DA EXTRAÇÃO")
    print("=" * 60)
    for r in resultados:
        nome = r["clube"]["nome"] or "???"
        n_jogadores = len(r["jogadores"])
        incompletos = []

        if not r["estadio"]["nome"]:
            incompletos.append("estádio")
        if not r["clube"]["ano_fundacao"]:
            incompletos.append("ano_fundacao")
        if not r["treinador"]["nome"]:
            incompletos.append("treinador")
        if n_jogadores < 5:
            incompletos.append(f"jogadores (só {n_jogadores}, mínimo 5)")
        n_sem_data = sum(1 for j in r["jogadores"] if not j["data_nascimento"])
        if n_sem_data:
            incompletos.append(f"{n_sem_data} jogador(es) sem data de nascimento")
        n_sem_numero = sum(1 for j in r["jogadores"] if j["numero_camisola"] is None)
        if n_sem_numero:
            incompletos.append(f"{n_sem_numero} jogador(es) sem número de camisola")
        n_sem_nacionalidade = sum(1 for j in r["jogadores"] if not j["nacionalidade"])
        if n_sem_nacionalidade:
            incompletos.append(f"{n_sem_nacionalidade} jogador(es) sem nacionalidade")

        status = "OK" if not incompletos else "INCOMPLETO"
        print(f"- {nome}: {n_jogadores} jogadores extraídos [{status}]")
        if incompletos:
            print(f"    campos em falta: {', '.join(incompletos)}")
    print("=" * 60)


def main() -> None:
    resultados = [scrape_clube(config) for config in CLUBES]

    with open("clubes_algarve.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    log.info("JSON escrito em clubes_algarve.json")
    imprimir_resumo(resultados)


if __name__ == "__main__":
    main()
