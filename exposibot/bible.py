"""Busca o texto bíblico real (best-effort) para acompanhar a pesquisa.

Usa a API pública "A Bíblia Digital" (abibliadigital.com.br). É um recurso
de apoio: se a referência não for reconhecida, a API estiver fora do ar, ou
o host não estiver liberado na rede (ex: plano free do PythonAnywhere), a
função simplesmente retorna None e o resto do app segue funcionando.
"""

import os
import re

import requests

BASE_URL = "https://www.abibliadigital.com.br/api"
DEFAULT_VERSION = "nvi"

# Abreviações usadas pela API, mapeadas a partir dos nomes/variações em português.
BOOK_ABBREVIATIONS = {
    "genesis": "gn", "gênesis": "gn",
    "exodo": "ex", "êxodo": "ex",
    "levitico": "lv", "levítico": "lv",
    "numeros": "nm", "números": "nm",
    "deuteronomio": "dt", "deuteronômio": "dt",
    "josue": "js", "josué": "js",
    "juizes": "jz", "juízes": "jz",
    "rute": "rt",
    "1samuel": "1sm", "1 samuel": "1sm",
    "2samuel": "2sm", "2 samuel": "2sm",
    "1reis": "1rs", "1 reis": "1rs",
    "2reis": "2rs", "2 reis": "2rs",
    "1cronicas": "1cr", "1 crônicas": "1cr", "1crônicas": "1cr",
    "2cronicas": "2cr", "2 crônicas": "2cr", "2crônicas": "2cr",
    "esdras": "ed",
    "neemias": "ne",
    "ester": "et",
    "jo": "job", "job": "job", "jó": "job",
    "salmos": "sl", "salmo": "sl",
    "proverbios": "pv", "provérbios": "pv",
    "eclesiastes": "ec",
    "cantares": "ct", "cânticos": "ct", "canticos": "ct",
    "isaias": "is", "isaías": "is",
    "jeremias": "jr",
    "lamentacoes": "lm", "lamentações": "lm",
    "ezequiel": "ez",
    "daniel": "dn",
    "oseias": "os", "oséias": "os",
    "joel": "jl",
    "amos": "am", "amós": "am",
    "obadias": "ob",
    "jonas": "jn",
    "miqueias": "mq", "miquéias": "mq",
    "naum": "na",
    "habacuque": "hc",
    "sofonias": "sf",
    "ageu": "ag",
    "zacarias": "zc",
    "malaquias": "ml",
    "mateus": "mt",
    "marcos": "mc",
    "lucas": "lc",
    "joao": "jo", "joão": "jo",
    "atos": "at",
    "romanos": "rm",
    "1corintios": "1co", "1 coríntios": "1co", "1coríntios": "1co",
    "2corintios": "2co", "2 coríntios": "2co", "2coríntios": "2co",
    "galatas": "gl", "gálatas": "gl",
    "efesios": "ef", "efésios": "ef",
    "filipenses": "fp",
    "colossenses": "cl",
    "1tessalonicenses": "1ts", "1 tessalonicenses": "1ts",
    "2tessalonicenses": "2ts", "2 tessalonicenses": "2ts",
    "1timoteo": "1tm", "1 timóteo": "1tm", "1timóteo": "1tm",
    "2timoteo": "2tm", "2 timóteo": "2tm", "2timóteo": "2tm",
    "tito": "tt",
    "filemom": "fm",
    "hebreus": "hb",
    "tiago": "tg",
    "1pedro": "1pe", "1 pedro": "1pe",
    "2pedro": "2pe", "2 pedro": "2pe",
    "1joao": "1jo", "1 joão": "1jo", "1joão": "1jo",
    "2joao": "2jo", "2 joão": "2jo", "2joão": "2jo",
    "3joao": "3jo", "3 joão": "3jo", "3joão": "3jo",
    "judas": "jd",
    "apocalipse": "ap",
}

REFERENCE_RE = re.compile(
    r"^\s*(?P<book>[1-3]?\s*[A-Za-zÀ-ÿ]+)\s+(?P<chapter>\d+)"
    r"(?::(?P<v_start>\d+)(?:-(?P<v_end>\d+))?)?\s*$"
)


def _normalize_book(raw):
    key = raw.strip().lower().replace(".", "")
    key_compact = re.sub(r"\s+", "", key)
    return BOOK_ABBREVIATIONS.get(key) or BOOK_ABBREVIATIONS.get(key_compact)


def parse_reference(reference):
    """'Romanos 8:28-30' -> ('rm', 8, 28, 30). Retorna None se não reconhecer."""
    if not reference:
        return None
    match = REFERENCE_RE.match(reference)
    if not match:
        return None

    book = _normalize_book(match.group("book"))
    if not book:
        return None

    chapter = int(match.group("chapter"))
    v_start = int(match.group("v_start")) if match.group("v_start") else None
    v_end = int(match.group("v_end")) if match.group("v_end") else v_start
    return book, chapter, v_start, v_end


def fetch_passage(reference, version=DEFAULT_VERSION, timeout=6):
    """Retorna {'version': str, 'text': str} ou None (falha graciosa)."""
    parsed = parse_reference(reference)
    if not parsed:
        return None

    book, chapter, v_start, v_end = parsed
    headers = {}
    token = os.getenv("BIBLE_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(
            f"{BASE_URL}/verses/{version}/{book}/{chapter}",
            headers=headers,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        verses = data.get("verses", [])
        if not verses:
            return None

        if v_start:
            verses = [v for v in verses if v_start <= v.get("number", 0) <= (v_end or v_start)]
            if not verses:
                return None

        text = "\n".join(f"{v['number']}. {v['text']}" for v in verses)
        return {"version": version.upper(), "text": text}
    except Exception:
        return None
