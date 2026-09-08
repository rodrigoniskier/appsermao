"""Texto bíblico e metadados para seleção guiada de passagens."""

import os
import re

import requests

BASE_URL = "https://www.abibliadigital.com.br/api"
DEFAULT_VERSION = "nvi"

BOOK_CATALOG = [
    ("Gênesis", "gn", 50), ("Êxodo", "ex", 40), ("Levítico", "lv", 27),
    ("Números", "nm", 36), ("Deuteronômio", "dt", 34), ("Josué", "js", 24),
    ("Juízes", "jz", 21), ("Rute", "rt", 4), ("1 Samuel", "1sm", 31),
    ("2 Samuel", "2sm", 24), ("1 Reis", "1rs", 22), ("2 Reis", "2rs", 25),
    ("1 Crônicas", "1cr", 29), ("2 Crônicas", "2cr", 36), ("Esdras", "ed", 10),
    ("Neemias", "ne", 13), ("Ester", "et", 10), ("Jó", "job", 42),
    ("Salmos", "sl", 150), ("Provérbios", "pv", 31), ("Eclesiastes", "ec", 12),
    ("Cantares", "ct", 8), ("Isaías", "is", 66), ("Jeremias", "jr", 52),
    ("Lamentações", "lm", 5), ("Ezequiel", "ez", 48), ("Daniel", "dn", 12),
    ("Oseias", "os", 14), ("Joel", "jl", 3), ("Amós", "am", 9),
    ("Obadias", "ob", 1), ("Jonas", "jn", 4), ("Miqueias", "mq", 7),
    ("Naum", "na", 3), ("Habacuque", "hc", 3), ("Sofonias", "sf", 3),
    ("Ageu", "ag", 2), ("Zacarias", "zc", 14), ("Malaquias", "ml", 4),
    ("Mateus", "mt", 28), ("Marcos", "mc", 16), ("Lucas", "lc", 24),
    ("João", "jo", 21), ("Atos", "at", 28), ("Romanos", "rm", 16),
    ("1 Coríntios", "1co", 16), ("2 Coríntios", "2co", 13), ("Gálatas", "gl", 6),
    ("Efésios", "ef", 6), ("Filipenses", "fp", 4), ("Colossenses", "cl", 4),
    ("1 Tessalonicenses", "1ts", 5), ("2 Tessalonicenses", "2ts", 3),
    ("1 Timóteo", "1tm", 6), ("2 Timóteo", "2tm", 4), ("Tito", "tt", 3),
    ("Filemom", "fm", 1), ("Hebreus", "hb", 13), ("Tiago", "tg", 5),
    ("1 Pedro", "1pe", 5), ("2 Pedro", "2pe", 3), ("1 João", "1jo", 5),
    ("2 João", "2jo", 1), ("3 João", "3jo", 1), ("Judas", "jd", 1),
    ("Apocalipse", "ap", 22),
]

BOOK_NAMES_BY_ABBR = {abbr: name for name, abbr, _chapters in BOOK_CATALOG}

BOOK_ABBREVIATIONS = {
    "genesis": "gn", "gênesis": "gn", "exodo": "ex", "êxodo": "ex",
    "levitico": "lv", "levítico": "lv", "numeros": "nm", "números": "nm",
    "deuteronomio": "dt", "deuteronômio": "dt", "josue": "js", "josué": "js",
    "juizes": "jz", "juízes": "jz", "rute": "rt", "1samuel": "1sm", "1 samuel": "1sm",
    "2samuel": "2sm", "2 samuel": "2sm", "1reis": "1rs", "1 reis": "1rs",
    "2reis": "2rs", "2 reis": "2rs", "1cronicas": "1cr", "1 crônicas": "1cr", "1crônicas": "1cr",
    "2cronicas": "2cr", "2 crônicas": "2cr", "2crônicas": "2cr", "esdras": "ed",
    "neemias": "ne", "ester": "et", "jo": "job", "job": "job", "jó": "job",
    "salmos": "sl", "salmo": "sl", "proverbios": "pv", "provérbios": "pv",
    "eclesiastes": "ec", "cantares": "ct", "cânticos": "ct", "canticos": "ct",
    "isaias": "is", "isaías": "is", "jeremias": "jr", "lamentacoes": "lm", "lamentações": "lm",
    "ezequiel": "ez", "daniel": "dn", "oseias": "os", "oséias": "os", "joel": "jl",
    "amos": "am", "amós": "am", "obadias": "ob", "jonas": "jn", "miqueias": "mq", "miquéias": "mq",
    "naum": "na", "habacuque": "hc", "sofonias": "sf", "ageu": "ag", "zacarias": "zc", "malaquias": "ml",
    "mateus": "mt", "marcos": "mc", "lucas": "lc", "joao": "jo", "joão": "jo", "atos": "at",
    "romanos": "rm", "1corintios": "1co", "1 coríntios": "1co", "1coríntios": "1co",
    "2corintios": "2co", "2 coríntios": "2co", "2coríntios": "2co", "galatas": "gl", "gálatas": "gl",
    "efesios": "ef", "efésios": "ef", "filipenses": "fp", "colossenses": "cl",
    "1tessalonicenses": "1ts", "1 tessalonicenses": "1ts", "2tessalonicenses": "2ts", "2 tessalonicenses": "2ts",
    "1timoteo": "1tm", "1 timóteo": "1tm", "1timóteo": "1tm", "2timoteo": "2tm", "2 timóteo": "2tm", "2timóteo": "2tm",
    "tito": "tt", "filemom": "fm", "hebreus": "hb", "tiago": "tg", "1pedro": "1pe", "1 pedro": "1pe",
    "2pedro": "2pe", "2 pedro": "2pe", "1joao": "1jo", "1 joão": "1jo", "1joão": "1jo",
    "2joao": "2jo", "2 joão": "2jo", "2joão": "2jo", "3joao": "3jo", "3 joão": "3jo", "3joão": "3jo",
    "judas": "jd", "apocalipse": "ap",
}

REFERENCE_RE = re.compile(
    r"^\s*(?P<book>[1-3]?\s*[A-Za-zÀ-ÿ]+)\s+(?P<chapter>\d+)"
    r"(?::(?P<v_start>\d+)(?:-(?P<v_end>\d+))?)?\s*$"
)


def catalog():
    return [
        {"name": name, "abbr": abbr, "chapters": chapters}
        for name, abbr, chapters in BOOK_CATALOG
    ]


def _normalize_book(raw):
    key = raw.strip().lower().replace(".", "")
    key_compact = re.sub(r"\s+", "", key)
    if key in BOOK_NAMES_BY_ABBR:
        return key
    return BOOK_ABBREVIATIONS.get(key) or BOOK_ABBREVIATIONS.get(key_compact)


def parse_reference(reference):
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


def canonical_reference(book_abbr, chapter, v_start=None, v_end=None):
    name = BOOK_NAMES_BY_ABBR.get(book_abbr)
    if not name:
        return None
    ref = f"{name} {int(chapter)}"
    if v_start:
        ref += f":{int(v_start)}"
        if v_end and int(v_end) != int(v_start):
            ref += f"-{int(v_end)}"
    return ref


def fetch_chapter(book, chapter, version=DEFAULT_VERSION, timeout=6):
    if book not in BOOK_NAMES_BY_ABBR:
        return None
    headers = {}
    token = os.getenv("BIBLE_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(
            f"{BASE_URL}/verses/{version}/{book}/{int(chapter)}",
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        verses = data.get("verses", [])
        if not verses:
            return None
        return {
            "version": version.upper(),
            "book": book,
            "chapter": int(chapter),
            "verses": [
                {"number": int(v["number"]), "text": str(v["text"])}
                for v in verses
                if "number" in v and "text" in v
            ],
        }
    except (requests.RequestException, ValueError, TypeError, KeyError):
        return None


def fetch_passage(reference, version=DEFAULT_VERSION, timeout=6):
    parsed = parse_reference(reference)
    if not parsed:
        return None
    book, chapter, v_start, v_end = parsed
    chapter_data = fetch_chapter(book, chapter, version=version, timeout=timeout)
    if not chapter_data:
        return None
    verses = chapter_data["verses"]
    if v_start:
        verses = [v for v in verses if v_start <= v["number"] <= (v_end or v_start)]
        if not verses:
            return None
    text = "\n".join(f"{v['number']}. {v['text']}" for v in verses)
    return {"version": version.upper(), "text": text}
