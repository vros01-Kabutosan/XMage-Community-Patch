#!/usr/bin/env python3
"""Descarga y convierte 75 mazos oficiales de Magic Online.

Una sola ejecución:
  * preflight no destructivo;
  * 25 mazos distintos 60+15 de Standard, Pioneer y Modern;
  * validación de nombres, legalidad y copias mediante Scryfall;
  * Forge .dck, XMage .txt y XMage_DCK .dck nativo para Load.

Solo instala la carpeta ``MTGO`` cuando el resultado completo es 75/75. Los
proyectos Goldfish y MTGTop8 no se leen, no se modifican y no se eliminan.
"""

import json
import math
import os
import re
import shutil
import sys
import tempfile
import time
import traceback
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter


BASE = "https://www.mtgo.com"
INDEX_URL = BASE + "/decklists"
FORMATS = ("Standard", "Pioneer", "Modern")
TOP_N = 25
MAX_CONSECUTIVE_UNAVAILABLE = 3
MAX_EVENTS_PER_FORMAT = 20
MTGO_PAUSE = 0.8
SCRYFALL_PAUSE = 0.55
SCRYFALL_LOCKOUT = 5.0
DATA_MARKER = "window.MTGO.decklists.data = "
DATA_ASSIGNMENT = re.compile(
    r"window\s*\.\s*MTGO\s*\.\s*decklists\s*\.\s*data\s*=\s*",
    re.I,
)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "MTGO")
STAGING = os.path.join(HERE, "MTGO.__building__")
BACKUP = os.path.join(HERE, "MTGO.__previous__")
LOG_PATH = os.path.join(HERE, "mtgo_3_formatos_fusionado.log")
LOCK_PATH = os.path.join(HERE, "mtgo_3_formatos_fusionado.lock")
CACHE_PATH = os.path.join(HERE, "scryfall_mtgo_cache.json")

MTGO_LAST_REQUEST = 0.0
SCRYFALL_LAST_REQUEST = 0.0
EVENT_CACHE = {}

COLOR_NAMES = {
    frozenset(): "Colorless",
    frozenset("W"): "Mono White",
    frozenset("U"): "Mono Blue",
    frozenset("B"): "Mono Black",
    frozenset("R"): "Mono Red",
    frozenset("G"): "Mono Green",
    frozenset("WU"): "Azorius",
    frozenset("UB"): "Dimir",
    frozenset("BR"): "Rakdos",
    frozenset("RG"): "Gruul",
    frozenset("GW"): "Selesnya",
    frozenset("WB"): "Orzhov",
    frozenset("UR"): "Izzet",
    frozenset("BG"): "Golgari",
    frozenset("RW"): "Boros",
    frozenset("GU"): "Simic",
    frozenset("WUB"): "Esper",
    frozenset("UBR"): "Grixis",
    frozenset("BRG"): "Jund",
    frozenset("RGW"): "Naya",
    frozenset("GWU"): "Bant",
    frozenset("WBG"): "Abzan",
    frozenset("URW"): "Jeskai",
    frozenset("BGU"): "Sultai",
    frozenset("RWB"): "Mardu",
    frozenset("GUR"): "Temur",
}


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


def log(text):
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), text, flush=True)


def safe_input(prompt):
    try:
        return input(prompt)
    except EOFError:
        return ""


def acquire_instance_lock():
    handle = open(LOCK_PATH, "a+b")
    if os.path.getsize(LOCK_PATH) == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, IOError):
        handle.close()
        return None
    return handle


def release_instance_lock(handle):
    if not handle:
        return
    try:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


class WebSession:
    def get(self, url, referer=None, timeout=40):
        global MTGO_LAST_REQUEST
        wait = MTGO_PAUSE - (time.monotonic() - MTGO_LAST_REQUEST)
        if wait > 0:
            time.sleep(wait)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.7",
        }
        if referer:
            headers["Referer"] = referer
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                status = response.getcode()
                final_url = response.geturl()
        except urllib.error.HTTPError as error:
            body = error.read()
            status = error.code
            final_url = error.geturl()
        finally:
            MTGO_LAST_REQUEST = time.monotonic()
        return status, final_url, body.decode("utf-8", errors="replace")


def event_links(index_html, fmt):
    pattern = re.compile(r'''href=["']([^"']*/decklist/[^"']+)["']''', re.I)
    wanted = "/decklist/" + fmt.casefold() + "-"
    found = []
    seen = set()
    for href in pattern.findall(index_html):
        url = urllib.parse.urljoin(BASE, href.replace("&amp;", "&"))
        if wanted not in url.casefold() or url in seen:
            continue
        seen.add(url)
        found.append(url)

    def priority(url):
        lowered = url.casefold()
        competitive = any(word in lowered for word in ("challenge", "showcase", "qualifier"))
        league = "-league-" in lowered
        return (not competitive, league)

    return sorted(found, key=priority)


def _canonical_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _deck_score(value):
    """Puntúa estructuras de mazo sin confundirlas con clasificaciones."""
    if not isinstance(value, dict):
        return 0
    keys = {_canonical_key(key) for key in value}
    score = 0
    if keys & {"maindeck", "mainboard", "deckmain"}:
        score += 3
    if keys & {"sideboarddeck", "sideboard", "decksideboard"}:
        score += 3
    if keys & {"loginid", "player", "playername", "screenname"}:
        score += 1
    return score


def _deck_list_score(value):
    if not isinstance(value, list) or not value:
        return 0
    scores = [_deck_score(item) for item in value if isinstance(item, dict)]
    if not scores:
        return 0
    convincing = sum(score >= 3 for score in scores)
    return convincing * 100 + sum(scores)


def _find_decklists(value):
    """Busca recursivamente la lista real aunque MTGO añada envoltorios."""
    best = (0, None, None)

    def visit(node, container=None, depth=0):
        nonlocal best
        if depth > 12:
            return
        score = _deck_list_score(node)
        if score > best[0]:
            best = (score, node, container)
        if isinstance(node, dict):
            ordered = sorted(
                node.items(),
                key=lambda item: _canonical_key(item[0]) not in {
                    "decklists", "decks", "data", "event", "payload", "result"
                },
            )
            for _, child in ordered:
                if isinstance(child, (dict, list)):
                    visit(child, node, depth + 1)
        elif isinstance(node, list):
            for child in node:
                if isinstance(child, (dict, list)):
                    visit(child, container, depth + 1)

    visit(value)
    return best[1], best[2]


def _first_value(mapping, aliases):
    if not isinstance(mapping, dict):
        return None
    by_key = {_canonical_key(key): value for key, value in mapping.items()}
    for alias in aliases:
        if alias in by_key:
            return by_key[alias]
    return None


def _normalise_deck(deck):
    if not isinstance(deck, dict):
        return deck
    normalised = dict(deck)
    main = _first_value(deck, ("maindeck", "mainboard", "deckmain"))
    side = _first_value(deck, ("sideboarddeck", "sideboard", "decksideboard"))
    if main is not None:
        normalised["main_deck"] = main
    if side is not None:
        normalised["sideboard_deck"] = side
    login_id = _first_value(deck, ("loginid", "userid", "playerid"))
    if login_id is not None:
        normalised["loginid"] = login_id
    if not normalised.get("player"):
        player = _first_value(deck, ("playername", "screenname", "loginid"))
        if player is not None:
            normalised["player"] = player
    return normalised


def extract_event_data(html):
    match = DATA_ASSIGNMENT.search(html)
    if match is None:
        start = html.find(DATA_MARKER)
        if start < 0:
            raise ValueError("no aparece el JSON de MTGO")
        start += len(DATA_MARKER)
    else:
        start = match.end()
    data, _ = json.JSONDecoder().raw_decode(html[start:].lstrip())
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, (dict, list)):
        raise ValueError("estructura JSON de MTGO inesperada")

    decks, container = _find_decklists(data)
    if decks is None:
        raise ValueError("estructura JSON de MTGO sin una lista de mazos reconocible")
    result = dict(data) if isinstance(data, dict) else {}
    if isinstance(container, dict):
        for key, value in container.items():
            result.setdefault(key, value)
    result["decklists"] = [_normalise_deck(deck) for deck in decks]
    return result


def fetch_event(session, url):
    if url in EVENT_CACHE:
        return EVENT_CACHE[url]
    status, final_url, html = session.get(url, INDEX_URL)
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {final_url}")
    data = extract_event_data(html)
    EVENT_CACHE[url] = data
    return data


def raw_rows(deck, section):
    merged = []
    position = {}
    for card in deck.get(section) or []:
        try:
            quantity = int(_first_value(card, ("qty", "quantity", "count")) or 0)
        except (TypeError, ValueError):
            quantity = 0
        attributes = _first_value(card, ("cardattributes", "card")) or {}
        name = _first_value(attributes, ("cardname", "name"))
        if not name:
            name = _first_value(card, ("cardname", "name"))
        name = re.sub(r"\s+", " ", str(name or "")).strip()
        if quantity <= 0 or not name:
            return []
        key = name.casefold()
        if key in position:
            index = position[key]
            merged[index] = (merged[index][0] + quantity, merged[index][1])
        else:
            position[key] = len(merged)
            merged.append((quantity, name))
    return merged


def raw_signature(main, side):
    rows = [("M", quantity, name.casefold()) for quantity, name in main]
    rows.extend(("S", quantity, name.casefold()) for quantity, name in side)
    return tuple(sorted(rows))


def rank_map(data):
    output = {}
    final_rank = _first_value(data, ("finalrank", "finalstandings", "rankings")) or []
    standings = _first_value(data, ("standings", "players")) or []
    for row in final_rank:
        try:
            login_id = _first_value(row, ("loginid", "userid", "playerid"))
            rank = _first_value(row, ("rank", "place", "position"))
            output[str(login_id)] = int(rank)
        except (TypeError, ValueError):
            pass
    for row in standings:
        key = str(_first_value(row, ("loginid", "userid", "playerid")))
        if key in output:
            continue
        try:
            output[key] = int(_first_value(row, ("rank", "place", "position")))
        except (TypeError, ValueError):
            pass
    return output


def event_candidates(data):
    ranks = rank_map(data)
    candidates = []
    for order, deck in enumerate(data.get("decklists") or [], 1):
        main = raw_rows(deck, "main_deck")
        side = raw_rows(deck, "sideboard_deck")
        main_count = sum(quantity for quantity, _ in main)
        side_count = sum(quantity for quantity, _ in side)
        if (main_count, side_count) != (60, 15):
            continue
        login_id = str(deck.get("loginid") or "")
        candidates.append({
            "deck": deck,
            "main_raw": main,
            "side_raw": side,
            "raw_fingerprint": raw_signature(main, side),
            "rank": ranks.get(login_id, 10000 + order),
            "player": str(deck.get("player") or f"Player_{order}"),
            "event_id": str(data.get("event_id") or data.get("tournamentid") or "event"),
            "event": str(data.get("description") or "MTGO Event"),
            "date": str(data.get("starttime") or "")[:10],
        })
    return sorted(candidates, key=lambda item: (item["rank"], item["player"].casefold()))


def preflight(session, index_html):
    print("\nPRECHECK: comprobando 25 mazos distintos 60+15 por formato", flush=True)
    results = {}
    for fmt in FORMATS:
        links = event_links(index_html, fmt)
        seen = set()
        checked = 0
        unavailable = 0
        log(f"PRECHECK [{fmt}] {len(links)} eventos localizados")
        for url in links[:MAX_EVENTS_PER_FORMAT]:
            if len(seen) >= TOP_N:
                break
            checked += 1
            try:
                data = fetch_event(session, url)
                candidates = event_candidates(data)
                before = len(seen)
                seen.update(item["raw_fingerprint"] for item in candidates)
                log(
                    f"PRECHECK [{fmt}] {data.get('description', 'evento')}: "
                    f"{len(candidates)} válidos, {len(seen) - before} nuevos"
                )
            except Exception as error:
                log(f"PRECHECK [{fmt}] evento omitido: {error}")
                unavailable = unavailable + 1 if "503" in str(error) else 0
                if unavailable >= MAX_CONSECUTIVE_UNAVAILABLE:
                    raise RuntimeError(
                        "MTGO no disponible (3 errores 503 consecutivos); "
                        "se conservan los mazos anteriores"
                    )
            else:
                unavailable = 0
        results[fmt] = min(len(seen), TOP_N)
        print(f"PRECHECK {fmt}: {results[fmt]}/{TOP_N}", flush=True)

    total = sum(results.values())
    print(f"PRECHECK TOTAL: {total}/{TOP_N * len(FORMATS)}", flush=True)
    if total != TOP_N * len(FORMATS):
        raise RuntimeError("preflight incompleto; no se ha limpiado ni modificado MTGO")
    print("PRECHECK APTO: comienza la construcción segura", flush=True)


def load_cache():
    try:
        with open(CACHE_PATH, encoding="utf-8") as source:
            data = json.load(source)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


CARD_CACHE = load_cache()


def save_cache():
    temp = CACHE_PATH + ".tmp"
    with open(temp, "w", encoding="utf-8") as output:
        json.dump(CARD_CACHE, output, ensure_ascii=False, indent=2)
    os.replace(temp, CACHE_PATH)


def wait_scryfall():
    delay = SCRYFALL_PAUSE - (time.monotonic() - SCRYFALL_LAST_REQUEST)
    if delay > 0:
        time.sleep(delay)


def scryfall_request(url, payload=None, missing_ok=False):
    global SCRYFALL_LAST_REQUEST
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "User-Agent": "MTGO-Forge-XMage/1.0 (personal deck exporter)",
        "Accept": "application/json",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"
    for attempt in range(5):
        wait_scryfall()
        request = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                result = json.load(response)
            SCRYFALL_LAST_REQUEST = time.monotonic()
            return result
        except urllib.error.HTTPError as error:
            SCRYFALL_LAST_REQUEST = time.monotonic()
            if error.code in (400, 404) and missing_ok:
                return None
            if error.code == 429:
                try:
                    server_wait = float(error.headers.get("Retry-After", "0"))
                except (TypeError, ValueError):
                    server_wait = 0.0
                delay = max(SCRYFALL_LOCKOUT, server_wait)
                log(f"Scryfall 429; pausa obligatoria de {delay:.0f} s")
                time.sleep(delay)
            elif attempt < 4:
                time.sleep(2 + attempt)
            else:
                raise
        except Exception:
            SCRYFALL_LAST_REQUEST = time.monotonic()
            if attempt == 4:
                raise
            time.sleep(2 + attempt)
    return None


def cache_card(card, *aliases):
    if not isinstance(card, dict) or not card.get("name"):
        return
    names = [card.get("name", ""), *aliases]
    names.extend(face.get("name", "") for face in (card.get("card_faces") or []))
    for name in names:
        if name:
            CARD_CACHE[name.casefold()] = card


def prefetch_cards(rows):
    pending = []
    seen = set()
    for _, name in rows:
        key = name.casefold()
        if key not in CARD_CACHE and key not in seen:
            seen.add(key)
            pending.append(name)
    for start in range(0, len(pending), 75):
        batch = pending[start:start + 75]
        response = scryfall_request(
            "https://api.scryfall.com/cards/collection",
            {"identifiers": [{"name": name} for name in batch]},
        )
        for card in (response or {}).get("data", []):
            cache_card(card)
        log(f"Scryfall lote {min(start + len(batch), len(pending))}/{len(pending)}")


def get_card(name):
    key = name.casefold()
    if key in CARD_CACHE:
        return CARD_CACHE[key]
    queries = [name]
    if "/" in name and " // " not in name:
        queries.append(name.replace("/", " // "))
    if " // " in name:
        queries.append(name.split(" // ", 1)[0].strip())
    for query in queries:
        for mode in ("exact", "fuzzy"):
            url = "https://api.scryfall.com/cards/named?" + mode + "=" + urllib.parse.quote(query)
            card = scryfall_request(url, missing_ok=True)
            if card:
                cache_card(card, name, query)
                return CARD_CACHE.get(key)
    CARD_CACHE[key] = None
    return None


def resolve_and_merge(rows):
    output = []
    positions = {}
    errors = []
    for quantity, requested_name in rows:
        card = get_card(requested_name)
        if not card:
            errors.append(f"Scryfall no encuentra: {requested_name}")
            continue
        official = card.get("name", requested_name)
        identity = card.get("oracle_id") or official.casefold()
        if identity in positions:
            index = positions[identity]
            old = output[index]
            output[index] = (old[0] + quantity, old[1], old[2])
        else:
            positions[identity] = len(output)
            output.append((quantity, requested_name, card))
    return output, errors


def validate_resolved(main, side, fmt):
    errors = []
    main_count = sum(quantity for quantity, _, _ in main)
    side_count = sum(quantity for quantity, _, _ in side)
    if (main_count, side_count) != (60, 15):
        errors.append(f"tamaño {main_count}+{side_count}, se requiere 60+15")

    totals = {}
    info = {}
    for quantity, requested_name, card in main + side:
        official = card.get("name", requested_name)
        if card.get("legalities", {}).get(fmt.casefold()) != "legal":
            errors.append(f"ilegal en {fmt}: {official}")
        identity = card.get("oracle_id") or official.casefold()
        totals[identity] = totals.get(identity, 0) + quantity
        info[identity] = (official, card)

    for identity, quantity in totals.items():
        official, card = info[identity]
        rules = str(card.get("oracle_text") or "").casefold()
        unlimited = "any number of cards named" in rules or "a deck can have up to" in rules
        if "Basic Land" not in str(card.get("type_line") or "") and not unlimited and quantity > 4:
            errors.append(f"{quantity} copias: {official}")
    return errors


def resolved_fingerprint(main, side):
    rows = []
    for marker, cards in (("M", main), ("S", side)):
        for quantity, _, card in cards:
            identity = card.get("oracle_id") or card.get("name", "").casefold()
            rows.append((marker, quantity, identity))
    return tuple(sorted(rows))


def xmage_name(card, requested_name):
    full_name = card.get("name", requested_name)
    faces = card.get("card_faces") or []
    requested_key = requested_name.casefold()
    for face in faces:
        if str(face.get("name") or "").casefold() == requested_key:
            return face["name"]
    if faces and card.get("layout") in {
        "adventure", "transform", "modal_dfc", "reversible_card", "meld", "prototype"
    }:
        return faces[0].get("name") or requested_name
    return full_name


def dck_identity(card):
    set_code = str(card.get("set") or "").upper()
    number = str(card.get("collector_number") or "")
    if not set_code or not number:
        raise ValueError(f"sin SET:número para {card.get('name', 'carta')}")
    return set_code, number


def safe_component(text, fallback="MTGO"):
    normalized = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9 _-]", "", normalized)
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    return cleaned[:70] or fallback


def color_label(main):
    colors = set()
    for _, _, card in main:
        colors.update(card.get("color_identity") or [])
    key = frozenset(colors)
    if key in COLOR_NAMES:
        return COLOR_NAMES[key]
    if len(key) == 4:
        return "4C"
    if len(key) >= 5:
        return "5C"
    return "Multicolor"


def short_card_name(card):
    name = str(card.get("name") or "Card")
    return name.split(" // ", 1)[0].strip()


def descriptive_names(accepted_decks):
    """Genera Color + dos cartas distintivas sin inventar un arquetipo."""
    document_frequency = Counter()
    for item in accepted_decks:
        identities = set()
        for _, _, card in item["main"]:
            if "Land" in str(card.get("type_line") or ""):
                continue
            identity = card.get("oracle_id") or card.get("name", "").casefold()
            identities.add(identity)
        document_frequency.update(identities)

    total_decks = len(accepted_decks)
    output = []
    for item in accepted_decks:
        scored = []
        for quantity, _, card in item["main"]:
            if "Land" in str(card.get("type_line") or ""):
                continue
            identity = card.get("oracle_id") or card.get("name", "").casefold()
            frequency = document_frequency.get(identity, 1)
            rarity_weight = math.log((total_decks + 1) / (frequency + 1)) + 1.0
            quantity_weight = 1.0 + 0.35 * min(quantity, 4)
            scored.append((rarity_weight * quantity_weight, quantity, short_card_name(card)))
        scored.sort(key=lambda row: (-row[0], -row[1], row[2].casefold()))

        signatures = []
        seen_names = set()
        for _, _, name in scored:
            key = name.casefold()
            if key in seen_names:
                continue
            seen_names.add(key)
            signatures.append(name)
            if len(signatures) == 2:
                break
        parts = [color_label(item["main"]), *signatures]
        output.append(" - ".join(parts) if signatures else parts[0] + " Deck")
    return output


def deck_stem(index, descriptive_name):
    filename_name = descriptive_name.replace(" - ", " ")
    return f"{index:02d}_{safe_component(filename_name, 'MTGO_Deck')}"


def atomic_write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8", newline="\n") as output:
        output.write(content)
    os.replace(temporary, path)


def build_contents(name, main, side):
    forge = ["[metadata]", f"Name={name}", "[Main]"]
    forge.extend(f"{quantity} {card.get('name', requested)}" for quantity, requested, card in main)
    forge.append("[Sideboard]")
    forge.extend(f"{quantity} {card.get('name', requested)}" for quantity, requested, card in side)

    xmage = [f"{quantity} {xmage_name(card, requested)}" for quantity, requested, card in main]
    xmage.append("")
    xmage.extend(f"{quantity} {xmage_name(card, requested)}" for quantity, requested, card in side)

    dck = []
    for quantity, requested, card in main:
        set_code, number = dck_identity(card)
        dck.append(f"{quantity} [{set_code}:{number}] {xmage_name(card, requested)}")
    for quantity, requested, card in side:
        set_code, number = dck_identity(card)
        dck.append(f"SB: {quantity} [{set_code}:{number}] {xmage_name(card, requested)}")
    dck.extend(("LAYOUT MAIN", "LAYOUT SIDEBOARD"))
    return "\n".join(forge) + "\n", "\n".join(xmage) + "\n", "\n".join(dck) + "\n"


def verify_content(forge, xmage, dck):
    main_block, side_block = forge.split("[Main]\n", 1)[1].split("[Sideboard]\n", 1)
    forge_counts = (
        sum(map(int, re.findall(r"^(\d+)\s+", main_block, re.M))),
        sum(map(int, re.findall(r"^(\d+)\s+", side_block, re.M))),
    )
    parts = re.split(r"\n\s*\n", xmage, maxsplit=1)
    xmage_counts = (
        sum(map(int, re.findall(r"^(\d+)\s+", parts[0], re.M))),
        sum(map(int, re.findall(r"^(\d+)\s+", parts[1], re.M))) if len(parts) > 1 else 0,
    )
    dck_main = sum(map(int, re.findall(r"^(\d+)\s+\[[^]]+\]", dck, re.M)))
    dck_side = sum(map(int, re.findall(r"^SB:\s*(\d+)\s+\[[^]]+\]", dck, re.M)))
    if forge_counts != (60, 15) or xmage_counts != (60, 15) or (dck_main, dck_side) != (60, 15):
        raise ValueError(
            f"verificación fallida: Forge {forge_counts}, XMage {xmage_counts}, "
            f"DCK {(dck_main, dck_side)}"
        )
    if not dck.endswith("LAYOUT MAIN\nLAYOUT SIDEBOARD\n"):
        raise ValueError("faltan layouts XMage")


def prepare_staging():
    if os.path.isdir(STAGING):
        shutil.rmtree(STAGING)
    for engine in ("Forge", "XMage", "XMage_DCK"):
        for fmt in FORMATS:
            os.makedirs(os.path.join(STAGING, engine, fmt), exist_ok=True)
    log(f"CONSTRUCCIÓN TEMPORAL {STAGING}")


def write_outputs(fmt, stem, name, main, side):
    forge, xmage, dck = build_contents(name, main, side)
    verify_content(forge, xmage, dck)
    paths = (
        os.path.join(STAGING, "Forge", fmt, stem + ".dck"),
        os.path.join(STAGING, "XMage", fmt, stem + ".txt"),
        os.path.join(STAGING, "XMage_DCK", fmt, stem + ".dck"),
    )
    for path, content in zip(paths, (forge, xmage, dck)):
        atomic_write(path, content)
    return paths


def install_staging(root=ROOT, staging=STAGING, backup=BACKUP):
    if os.path.exists(root) and not os.path.isdir(root):
        raise RuntimeError(f"la ruta de salida existe y no es una carpeta: {root}")
    if os.path.isdir(backup):
        shutil.rmtree(backup)
    if os.path.isdir(root):
        shutil.copytree(root, backup)

    try:
        os.makedirs(root, exist_ok=True)
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)
        shutil.copytree(staging, root, dirs_exist_ok=True)

        installed = count_outputs(root)
        for engine in ("Forge", "XMage", "XMage_DCK"):
            if any(installed[engine][fmt] != TOP_N for fmt in FORMATS):
                raise RuntimeError(f"instalación final incorrecta en {engine}: {installed[engine]}")
    except Exception:
        if os.path.isdir(root):
            shutil.rmtree(root)
        if os.path.isdir(backup):
            shutil.copytree(backup, root)
        raise
    else:
        if os.path.isdir(backup):
            shutil.rmtree(backup)
        if os.path.isdir(staging):
            shutil.rmtree(staging)
        log(f"INSTALACIÓN LIMPIA COMPLETA {root}")


def process_format(session, index_html, fmt, overall_start):
    links = event_links(index_html, fmt)
    accepted_decks = []
    raw_seen = set()
    resolved_seen = set()
    unavailable = 0
    for url in links[:MAX_EVENTS_PER_FORMAT]:
        if len(accepted_decks) >= TOP_N:
            break
        try:
            data = fetch_event(session, url)
            candidates = event_candidates(data)
            names = []
            for candidate in candidates:
                if candidate["raw_fingerprint"] not in raw_seen:
                    names.extend(candidate["main_raw"] + candidate["side_raw"])
            prefetch_cards(names)
            log(f"[{fmt}] {data.get('description', 'evento')}: {len(candidates)} candidatos")
        except Exception as error:
            log(f"[{fmt}] evento omitido: {error}")
            unavailable = unavailable + 1 if "503" in str(error) else 0
            if unavailable >= MAX_CONSECUTIVE_UNAVAILABLE:
                raise RuntimeError(
                    "MTGO no disponible (3 errores 503 consecutivos); "
                    "se conservan los mazos anteriores"
                )
            continue
        unavailable = 0

        for candidate in candidates:
            if len(accepted_decks) >= TOP_N:
                break
            raw_key = candidate["raw_fingerprint"]
            if raw_key in raw_seen:
                continue
            raw_seen.add(raw_key)
            try:
                main, main_errors = resolve_and_merge(candidate["main_raw"])
                side, side_errors = resolve_and_merge(candidate["side_raw"])
                if main_errors or side_errors:
                    raise ValueError("; ".join(main_errors + side_errors))
                errors = validate_resolved(main, side, fmt)
                if errors:
                    raise ValueError("; ".join(errors))
                fingerprint = resolved_fingerprint(main, side)
                if fingerprint in resolved_seen:
                    raise ValueError("mazo duplicado exacto")
                resolved_seen.add(fingerprint)

                accepted_decks.append({
                    "candidate": candidate,
                    "main": main,
                    "side": side,
                })
                print(
                    f"[{fmt}] VALIDADO {len(accepted_decks)}/{TOP_N}: "
                    f"{candidate['player']}",
                    flush=True,
                )
            except Exception as error:
                log(f"[{fmt}] omitido {candidate['player']}: {error}")

    if len(accepted_decks) == TOP_N:
        names = descriptive_names(accepted_decks)
        for index, (item, name) in enumerate(zip(accepted_decks, names), 1):
            candidate = item["candidate"]
            stem = deck_stem(index, name)
            write_outputs(fmt, stem, name, item["main"], item["side"])
            overall = overall_start + index
            percent = overall * 100.0 / (TOP_N * len(FORMATS))
            log(f"NOMBRE [{fmt}] {candidate['player']} -> {name}")
            print(
                f"[{fmt}] OK {index}/{TOP_N} | TOTAL {overall}/75 "
                f"({percent:.1f}%) | {stem}",
                flush=True,
            )

    print(f"{fmt}: {len(accepted_decks)}/{TOP_N} completos", flush=True)
    return len(accepted_decks)


def count_outputs(root):
    result = {}
    for engine, extension in (("Forge", ".dck"), ("XMage", ".txt"), ("XMage_DCK", ".dck")):
        result[engine] = {}
        for fmt in FORMATS:
            folder = os.path.join(root, engine, fmt)
            result[engine][fmt] = sum(
                name.casefold().endswith(extension) for name in os.listdir(folder)
            )
    return result


def run(preflight_only=False):
    session = WebSession()
    print("INICIO", time.strftime("%Y-%m-%d %H:%M:%S"), flush=True)
    status, final_url, index_html = session.get(INDEX_URL)
    print(f"ÍNDICE MTGO: HTTP {status} | {len(index_html):,} bytes | {final_url}", flush=True)
    if status != 200 or len(index_html) < 10000:
        raise RuntimeError("no se puede leer el índice oficial; no se ha modificado MTGO")
    preflight(session, index_html)
    if preflight_only:
        print("MODO PREFLIGHT: no se ha creado, borrado ni modificado MTGO", flush=True)
        return

    prepare_staging()
    counts = {}
    overall = 0
    try:
        for fmt in FORMATS:
            counts[fmt] = process_format(session, index_html, fmt, overall)
            overall += counts[fmt]
        save_cache()
        if any(counts.get(fmt) != TOP_N for fmt in FORMATS):
            raise RuntimeError(f"construcción incompleta: {counts}; se conserva la colección anterior")

        files = count_outputs(STAGING)
        for engine in ("Forge", "XMage", "XMage_DCK"):
            if any(files[engine][fmt] != TOP_N for fmt in FORMATS):
                raise RuntimeError(f"recuento incorrecto en {engine}: {files[engine]}")
        install_staging()
    except Exception:
        if os.path.isdir(STAGING):
            shutil.rmtree(STAGING)
        raise

    print("\nRESULTADO FINAL", flush=True)
    for fmt in FORMATS:
        print(
            f"{fmt}: Forge 25/25 | XMage TXT 25/25 | XMage Load DCK 25/25",
            flush=True,
        )
    print("MAZOS: 75/75", flush=True)
    print("ARCHIVOS: 225/225", flush=True)
    print("ESTADO: PERFECTO", flush=True)


def self_test():
    sample_data = {
        "event_id": "123",
        "description": "Standard Challenge 32",
        "starttime": "2026-01-01 00:00:00.0",
        "decklists": [{
            "loginid": "7",
            "player": "Tester",
            "main_deck": [
                {"qty": "4", "card_attributes": {"card_name": "Lightning Bolt"}},
                {"qty": "56", "card_attributes": {"card_name": "Mountain"}},
            ],
            "sideboard_deck": [
                {"qty": "15", "card_attributes": {"card_name": "Island"}},
            ],
        }],
        "final_rank": [{"loginid": "7", "rank": "1"}],
    }
    sample_html = (
        '<a href="/decklist/standard-challenge-32-2026-01-01123">Evento</a>'
        '<script>' + DATA_MARKER + json.dumps(sample_data) + ';</script>'
    )
    assert event_links(sample_html, "Standard") == [
        "https://www.mtgo.com/decklist/standard-challenge-32-2026-01-01123"
    ]
    recovered = extract_event_data(sample_html)
    candidate = event_candidates(recovered)[0]
    assert sum(q for q, _ in candidate["main_raw"]) == 60
    assert sum(q for q, _ in candidate["side_raw"]) == 15
    assert candidate["rank"] == 1
    list_html = '<script>' + DATA_MARKER + json.dumps(sample_data["decklists"]) + ';</script>'
    assert extract_event_data(list_html)["decklists"][0]["player"] == "Tester"
    nested_html = '<script>' + DATA_MARKER + json.dumps({"data": sample_data}) + ';</script>'
    assert extract_event_data(nested_html)["decklists"][0]["player"] == "Tester"
    changed_deck = {
        "loginId": "8",
        "playerName": "Tester nuevo",
        "mainDeck": sample_data["decklists"][0]["main_deck"],
        "sideboard": sample_data["decklists"][0]["sideboard_deck"],
    }
    changed_html = (
        '<script>window . MTGO . decklists . data={"payload":{"event":'
        + json.dumps({"description": "Evento nuevo", "decks": [changed_deck]})
        + '}};</script>'
    )
    changed = extract_event_data(changed_html)
    assert changed["decklists"][0]["player"] == "Tester nuevo"
    assert sum(q for q, _ in event_candidates(changed)[0]["main_raw"]) == 60

    mock_main = [
        (4, "Lightning Bolt", {
            "name": "Lightning Bolt", "set": "m10", "collector_number": "146",
            "oracle_id": "bolt", "color_identity": ["R"], "type_line": "Instant",
        }),
        (56, "Mountain", {
            "name": "Mountain", "set": "m21", "collector_number": "312",
            "oracle_id": "mountain", "color_identity": ["R"], "type_line": "Basic Land — Mountain",
        }),
    ]
    mock_side = [
        (15, "Island", {
            "name": "Island", "set": "m21", "collector_number": "265",
            "oracle_id": "island", "color_identity": ["U"], "type_line": "Basic Land — Island",
        }),
    ]
    forge, xmage, dck = build_contents("Prueba", mock_main, mock_side)
    verify_content(forge, xmage, dck)
    assert "4 [M10:146] Lightning Bolt" in dck
    assert "SB: 15 [M21:265] Island" in dck
    named = descriptive_names([{"main": mock_main, "side": mock_side}])
    assert named == ["Mono Red - Lightning Bolt"]
    assert deck_stem(1, named[0]) == "01_Mono_Red_Lightning_Bolt"

    with tempfile.TemporaryDirectory() as temp_dir:
        test_root = os.path.join(temp_dir, "MTGO")
        test_staging = os.path.join(temp_dir, "MTGO.__building__")
        test_backup = os.path.join(temp_dir, "MTGO.__previous__")
        for engine, extension in (("Forge", ".dck"), ("XMage", ".txt"), ("XMage_DCK", ".dck")):
            for fmt in FORMATS:
                old_folder = os.path.join(test_root, engine, fmt)
                new_folder = os.path.join(test_staging, engine, fmt)
                os.makedirs(old_folder, exist_ok=True)
                os.makedirs(new_folder, exist_ok=True)
                with open(os.path.join(old_folder, "nombre_antiguo" + extension), "w", encoding="utf-8") as output:
                    output.write("old")
                for number in range(1, TOP_N + 1):
                    with open(os.path.join(new_folder, f"{number:02d}_nombre_nuevo" + extension), "w", encoding="utf-8") as output:
                        output.write("new")
        install_staging(test_root, test_staging, test_backup)
        installed = count_outputs(test_root)
        assert all(installed[engine][fmt] == TOP_N for engine in installed for fmt in FORMATS)
        assert not any("nombre_antiguo" in name for _, _, files in os.walk(test_root) for name in files)
        assert not os.path.exists(test_staging)
        assert not os.path.exists(test_backup)
    print("SELF-TEST OK", flush=True)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        instance_lock = acquire_instance_lock()
        if instance_lock is None:
            print("Ya hay otra ejecución de MTGO abierta. Ciérrala antes de continuar.")
        else:
            try:
                old_stdout = sys.stdout
                with open(LOG_PATH, "w", encoding="utf-8") as log_file:
                    sys.stdout = Tee(old_stdout, log_file)
                    try:
                        run(preflight_only="--preflight-only" in sys.argv)
                    except Exception as error:
                        print("ERROR GLOBAL", repr(error), flush=True)
                        traceback.print_exc()
                    finally:
                        print("LOG", LOG_PATH, flush=True)
                        sys.stdout = old_stdout
            finally:
                release_instance_lock(instance_lock)
