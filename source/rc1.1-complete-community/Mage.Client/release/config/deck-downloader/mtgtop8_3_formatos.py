#!/usr/bin/env python3
"""Descarga 25 mazos 60+15 de MTGTop8 en Forge y XMage.

Es una adaptación independiente del descargador estable de MTGGoldfish.
Solo borra y recrea su propia carpeta ``MTGTop8``.
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import parse_qs, urljoin, urlparse


DEPENDENCIAS = {
    "requests": "requests",
    "bs4": "beautifulsoup4",
    "selenium": "selenium",
    "undetected_chromedriver": "undetected-chromedriver",
    # undetected-chromedriver todavía usa distutils en Python 3.12+.
    "setuptools": "setuptools",
}
faltan = [paquete for modulo, paquete in DEPENDENCIAS.items()
          if importlib.util.find_spec(modulo) is None]
if faltan:
    subprocess.check_call([sys.executable, "-m", "pip", "install", *faltan])

import requests
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc


BASE = "https://www.mtgtop8.com"
FORMATS = {"Standard": "ST", "Pioneer": "PI", "Modern": "MO"}
TOP_N = 25
MAX_EVENTS = 40
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "MTGTop8")
LOG = os.path.join(HERE, "mtgtop8_3_formatos.log")
LOCK_PATH = os.path.join(HERE, "mtgtop8_3_formatos.lock")

SCRYFALL = requests.Session()
SCRYFALL.headers.update({
    "User-Agent": "MTGTop8-Forge-XMage/1.0 (personal deck exporter)",
    "Accept": "application/json",
})
CARD_CACHE = {}
LAST_SCRYFALL_REQUEST = 0.0
SCRYFALL_MIN_INTERVAL = 0.55
SCRYFALL_LOCKOUT = 5.0


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


def acquire_instance_lock():
    """Impide dos ejecuciones simultáneas sin dejar bloqueos obsoletos."""
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


def new_options():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    return options


def make_driver():
    try:
        driver = uc.Chrome(options=new_options())
    except Exception as error:
        match = re.search(r"Current browser version is\s*(\d+)", str(error), re.I)
        if not match:
            raise
        driver = uc.Chrome(options=new_options(), version_main=int(match.group(1)))
    driver.set_page_load_timeout(40)
    driver.set_script_timeout(40)
    return driver


def navigate(driver, url):
    log(f"CHROME {url}")
    try:
        driver.get(url)
    except TimeoutException:
        log("TIMEOUT: se usará el contenido que ya haya cargado")
        try:
            driver.execute_script("window.stop();")
        except WebDriverException:
            pass
    except WebDriverException as error:
        raise RuntimeError(f"Chrome no pudo abrir la página: {error}") from error

    for _ in range(20):
        text = (driver.execute_script("return document.body.innerText;") or "").strip()
        if text and not re.search(r"just a moment|checking your browser", text, re.I):
            return text
        time.sleep(1)
    text = (driver.execute_script("return document.body.innerText;") or "").strip()
    if re.search(r"just a moment|checking your browser|verify you are human", text, re.I):
        print("La web pide una verificación. Resuélvela en Chrome y pulsa ENTER aquí.", flush=True)
        input()
        driver.refresh()
        time.sleep(2)
        text = (driver.execute_script("return document.body.innerText;") or "").strip()
    return text


def unlock(driver):
    navigate(driver, f"{BASE}/format?f=ST")
    print("\nChrome está abierto en MTGTop8.", flush=True)
    print("Si aparece una verificación, resuélvela. Después pulsa ENTER aquí.", flush=True)
    input()


def clean_output():
    if os.path.isdir(ROOT):
        shutil.rmtree(ROOT, ignore_errors=True)
    for engine in ("Forge", "XMage"):
        for fmt in FORMATS:
            os.makedirs(os.path.join(ROOT, engine, fmt), exist_ok=True)
    log(f"LIMPIANDO {ROOT}")


def query_value(url, key):
    return parse_qs(urlparse(url).query).get(key, [None])[0]


def normalize_event_url(url):
    """Convierte los enlaces abreviados ``?e=...&d=...`` de MTGTop8."""
    parsed = urlparse(url)
    if parsed.path in {"", "/"} and query_value(url, "e") and query_value(url, "d"):
        return f"{BASE}/event?{parsed.query}"
    return url


def tournament_urls_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    output = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        url = urljoin(BASE, anchor["href"]).split("#", 1)[0]
        if "/event?" not in url or not query_value(url, "e"):
            continue
        if query_value(url, "d"):
            continue
        if url not in seen:
            seen.add(url)
            output.append(url)
    return output


def tournament_urls(driver, code):
    navigate(driver, f"{BASE}/format?f={code}")
    time.sleep(1)
    return tournament_urls_from_html(driver.page_source)


def deck_links_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    by_id = {}
    for anchor in soup.find_all("a", href=True):
        url = urljoin(BASE, anchor["href"]).split("#", 1)[0]
        url = normalize_event_url(url)
        if urlparse(url).path.casefold() != "/event":
            continue
        deck_id = query_value(url, "d")
        if not deck_id or not deck_id.isdigit():
            continue
        label = anchor.get_text(" ", strip=True)
        if label and label not in {"→", "←"} and "visual" not in label.casefold():
            by_id[deck_id] = (deck_id, label, url)
        elif deck_id not in by_id:
            by_id[deck_id] = (deck_id, "MTGTop8 deck", url)
    return list(by_id.values())


def deck_links(driver, event_url):
    navigate(driver, event_url)
    time.sleep(0.7)
    return deck_links_from_html(driver.page_source)


def export_url_from_html(html, deck_id):
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    for anchor in soup.find_all("a", href=True):
        url = urljoin(BASE, anchor["href"])
        path = urlparse(url).path.casefold()
        if query_value(url, "d") == deck_id and path in {"/mtgo", "/dec"}:
            candidates.append(url)
    for url in candidates:
        if urlparse(url).path.casefold() == "/mtgo":
            return url
    if candidates:
        return candidates[0]
    return f"{BASE}/mtgo?d={deck_id}"


def fetch_export_text(driver, url):
    """Lee el exportador dentro de Chrome sin activar una descarga."""
    log(f"FETCH {url}")
    result = driver.execute_async_script(
        """
        const url = arguments[0];
        const done = arguments[arguments.length - 1];
        fetch(url, {credentials: "include", cache: "no-store"})
          .then(async response => done({
              ok: response.ok,
              status: response.status,
              text: await response.text()
          }))
          .catch(error => done({ok: false, status: 0, error: String(error)}));
        """,
        url,
    )
    if not result or not result.get("ok"):
        status = (result or {}).get("status", 0)
        detail = (result or {}).get("error", "sin respuesta")
        raise RuntimeError(f"no se pudo leer el exportador (HTTP {status}): {detail}")
    text = result.get("text", "")
    if not text.strip():
        raise ValueError("el exportador devolvió un archivo vacío")
    return text


def parse_export(text):
    main = []
    side = []
    side_started = False
    for raw in text.replace("\r\n", "\n").splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.casefold().rstrip(":") in {"sideboard", "sb"}:
            side_started = True
            continue
        is_side = bool(re.match(r"^SB\s*:", line, re.I))
        line = re.sub(r"^SB\s*:\s*", "", line, flags=re.I)
        match = re.match(r"^(\d+)\s+(?:\[[^]]*\]\s*)?(.+?)\s*$", line)
        if not match:
            continue
        item = (int(match.group(1)), match.group(2).strip())
        (side if side_started or is_side else main).append(item)
    return merge_raw(main), merge_raw(side)


def merge_raw(rows):
    output = []
    position = {}
    for quantity, name in rows:
        key = re.sub(r"\s+", " ", name).strip().casefold()
        if key in position:
            index = position[key]
            output[index] = (output[index][0] + quantity, output[index][1])
        else:
            position[key] = len(output)
            output.append((quantity, name))
    return output


def wait_for_scryfall():
    global LAST_SCRYFALL_REQUEST
    delay = SCRYFALL_MIN_INTERVAL - (time.monotonic() - LAST_SCRYFALL_REQUEST)
    if delay > 0:
        time.sleep(delay)


def cache_card(card, *aliases):
    names = [card.get("name", ""), *aliases]
    names.extend(face.get("name", "") for face in (card.get("card_faces") or []))
    for name in names:
        if name:
            CARD_CACHE[name.casefold()] = card


def retry_after(response):
    try:
        server_wait = float(response.headers.get("Retry-After", "0"))
    except ValueError:
        server_wait = 0.0
    return max(SCRYFALL_LOCKOUT, server_wait)


def prefetch_cards(rows):
    """Resuelve hasta 75 nombres por petición con la API Collection."""
    pending = []
    seen = set()
    for _, name in rows:
        key = name.casefold()
        if key not in CARD_CACHE and key not in seen:
            seen.add(key)
            pending.append(name)

    for start in range(0, len(pending), 75):
        batch = pending[start:start + 75]
        if not batch:
            continue
        for attempt in range(5):
            wait_for_scryfall()
            try:
                response = SCRYFALL.post(
                    "https://api.scryfall.com/cards/collection",
                    json={"identifiers": [{"name": name} for name in batch]},
                    timeout=30,
                )
                global LAST_SCRYFALL_REQUEST
                LAST_SCRYFALL_REQUEST = time.monotonic()
                if response.status_code == 429:
                    wait = retry_after(response)
                    log(f"Scryfall 429; pausa obligatoria de {wait:.0f} s")
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                data = response.json()
                for card in data.get("data", []):
                    cache_card(card)
                for requested in batch:
                    key = requested.casefold()
                    if key in CARD_CACHE:
                        continue
                    for card in data.get("data", []):
                        aliases = [card.get("name", "")]
                        aliases.extend(face.get("name", "") for face in (card.get("card_faces") or []))
                        if key in {alias.casefold() for alias in aliases if alias}:
                            cache_card(card, requested)
                            break
                log(f"Scryfall lote: {len(batch)} nombres consultados")
                break
            except requests.RequestException as error:
                if attempt == 4:
                    log(f"Scryfall lote fallido: {error}")
                else:
                    time.sleep(2 + attempt)


def get_card(name):
    global LAST_SCRYFALL_REQUEST
    key = name.casefold()
    if key in CARD_CACHE:
        return CARD_CACHE[key]

    for mode in ("exact", "fuzzy"):
        for attempt in range(5):
            wait_for_scryfall()
            try:
                response = SCRYFALL.get(
                    "https://api.scryfall.com/cards/named",
                    params={mode: name}, timeout=20,
                )
                LAST_SCRYFALL_REQUEST = time.monotonic()
                if response.status_code == 429:
                    wait = retry_after(response)
                    log(f"Scryfall 429; pausa obligatoria de {wait:.0f} s")
                    time.sleep(wait)
                    continue
                if response.ok:
                    card = response.json()
                    cache_card(card, name)
                    return card
                break
            except requests.RequestException:
                if attempt == 4:
                    break
                time.sleep(1 + attempt)
    CARD_CACHE[key] = None
    return None


def resolve(rows):
    resolved = []
    errors = []
    for quantity, requested_name in rows:
        card = get_card(requested_name)
        if not card:
            errors.append(f"Scryfall no encuentra: {requested_name}")
            continue
        resolved.append((quantity, requested_name, card))
    return resolved, errors


def xmage_name(card, requested_name):
    full_name = card.get("name", requested_name)
    faces = card.get("card_faces") or []
    requested_key = requested_name.casefold()
    for face in faces:
        if face.get("name", "").casefold() == requested_key:
            return face["name"]
    if faces and card.get("layout") in {
        "adventure", "transform", "modal_dfc", "reversible_card",
        "meld", "prototype",
    }:
        return faces[0].get("name") or requested_name
    return full_name


def validate(main, side, fmt):
    errors = []
    main_count = sum(quantity for quantity, _, _ in main)
    side_count = sum(quantity for quantity, _, _ in side)
    if main_count != 60:
        errors.append(f"main {main_count}/60")
    if side_count != 15:
        errors.append(f"sideboard {side_count}/15")

    totals = {}
    card_info = {}
    for quantity, requested_name, card in main + side:
        official = card.get("name", requested_name)
        if card.get("legalities", {}).get(fmt.casefold()) != "legal":
            errors.append(f"ilegal en {fmt}: {official}")
        key = card.get("oracle_id", official.casefold())
        totals[key] = totals.get(key, 0) + quantity
        card_info[key] = (official, card)

    for key, quantity in totals.items():
        official, card = card_info[key]
        rules = card.get("oracle_text", "").casefold()
        unlimited = (
            "any number of cards named" in rules
            or "a deck can have up to" in rules
        )
        if "Basic Land" not in card.get("type_line", "") and not unlimited and quantity > 4:
            errors.append(f"{quantity} copias: {official}")
    return errors, main_count, side_count


def safe_stem(name, deck_id, index):
    stem = re.sub(r"[^A-Za-z0-9 _-]", "", name).strip().replace(" ", "_")
    return f"{index:02d}_{stem or 'MTGTop8'}_{deck_id}"


def write_deck(fmt, stem, name, main, side):
    forge_path = os.path.join(ROOT, "Forge", fmt, stem + ".dck")
    xmage_path = os.path.join(ROOT, "XMage", fmt, stem + ".txt")

    with open(forge_path, "w", encoding="utf-8") as output:
        output.write(f"[metadata]\nName={name}\n[Main]\n")
        for quantity, _, card in main:
            output.write(f"{quantity} {card.get('name')}\n")
        output.write("[Sideboard]\n")
        for quantity, _, card in side:
            output.write(f"{quantity} {card.get('name')}\n")

    with open(xmage_path, "w", encoding="utf-8") as output:
        for quantity, requested_name, card in main:
            output.write(f"{quantity} {xmage_name(card, requested_name)}\n")
        output.write("\n")
        for quantity, requested_name, card in side:
            output.write(f"{quantity} {xmage_name(card, requested_name)}\n")

    return forge_path, xmage_path


def verify_files(forge_path, xmage_path):
    with open(forge_path, encoding="utf-8") as source:
        forge = source.read()
    main_block, side_block = forge.split("[Main]\n", 1)[1].split("[Sideboard]\n", 1)
    forge_main = sum(int(value) for value in re.findall(r"^(\d+)\s+", main_block, re.M))
    forge_side = sum(int(value) for value in re.findall(r"^(\d+)\s+", side_block, re.M))

    with open(xmage_path, encoding="utf-8") as source:
        xmage = source.read().replace("\r\n", "\n")
    parts = re.split(r"\n\s*\n", xmage, maxsplit=1)
    xmage_main = sum(int(value) for value in re.findall(r"^(\d+)\s+", parts[0], re.M))
    xmage_side = sum(int(value) for value in re.findall(r"^(\d+)\s+", parts[1], re.M)) if len(parts) > 1 else 0
    if (forge_main, forge_side, xmage_main, xmage_side) != (60, 15, 60, 15):
        raise ValueError(
            f"verificación de archivos fallida: Forge {forge_main}+{forge_side}, "
            f"XMage {xmage_main}+{xmage_side}"
        )


def deck_fingerprint(main, side):
    main_key = [
        ("M", quantity, card.get("oracle_id", card.get("name", "").casefold()))
        for quantity, _, card in main
    ]
    side_key = [
        ("S", quantity, card.get("oracle_id", card.get("name", "").casefold()))
        for quantity, _, card in side
    ]
    return tuple(sorted(main_key + side_key))


def run():
    clean_output()
    total = 0
    driver = make_driver()
    unlock(driver)
    try:
        for fmt, code in FORMATS.items():
            accepted = 0
            processed = set()
            fingerprints = set()
            events = tournament_urls(driver, code)
            log(f"[{fmt}] {len(events)} eventos recientes encontrados")

            for event_url in events[:MAX_EVENTS]:
                if accepted >= TOP_N:
                    break
                try:
                    links = deck_links(driver, event_url)
                    log(f"[{fmt}] evento {query_value(event_url, 'e')}: {len(links)} mazos")
                except Exception as error:
                    log(f"[{fmt}] evento omitido {event_url}: {error}")
                    continue

                for deck_id, link_name, deck_url in links:
                    if accepted >= TOP_N:
                        break
                    if deck_id in processed:
                        continue
                    processed.add(deck_id)
                    try:
                        navigate(driver, deck_url)
                        time.sleep(0.4)
                        export_url = export_url_from_html(driver.page_source, deck_id)
                        export_text = fetch_export_text(driver, export_url)
                        main_raw, side_raw = parse_export(export_text)
                        raw_counts = (sum(q for q, _ in main_raw), sum(q for q, _ in side_raw))
                        log(f"[{fmt}] {deck_id}: detectado {raw_counts[0]}+{raw_counts[1]} ({link_name})")
                        if raw_counts != (60, 15):
                            raise ValueError(f"la exportación no es 60+15: {raw_counts[0]}+{raw_counts[1]}")

                        prefetch_cards(main_raw + side_raw)
                        main, main_errors = resolve(main_raw)
                        side, side_errors = resolve(side_raw)
                        if main_errors or side_errors:
                            raise ValueError("; ".join(main_errors + side_errors))
                        errors, main_count, side_count = validate(main, side, fmt)
                        if errors:
                            raise ValueError("; ".join(errors))

                        fingerprint = deck_fingerprint(main, side)
                        if fingerprint in fingerprints:
                            raise ValueError("mazo duplicado")
                        fingerprints.add(fingerprint)

                        stem = safe_stem(link_name, deck_id, accepted + 1)
                        forge_path, xmage_path = write_deck(fmt, stem, link_name, main, side)
                        verify_files(forge_path, xmage_path)
                        accepted += 1
                        total += 1
                        print(f"[{fmt}] OK {accepted}/{TOP_N}: {stem} ({main_count}+{side_count})", flush=True)
                    except Exception as error:
                        log(f"[{fmt}] omitido {deck_id}: {error}")
                    time.sleep(0.25)

            print(f"{fmt}: {accepted}/{TOP_N} exportados", flush=True)
        print(f"TOTAL: {total}/{TOP_N * len(FORMATS)}", flush=True)
    finally:
        driver.quit()


def self_test():
    sample = """// Deck file created with mtgtop8.com
// NAME : Test
4 [] Lightning Bolt
56 [] Mountain
SB:  3 [NPH] Torpor Orb
SB:  12 [] Island
"""
    main, side = parse_export(sample)
    assert main == [(4, "Lightning Bolt"), (56, "Mountain")]
    assert side == [(3, "Torpor Orb"), (12, "Island")]

    event_html = """
    <a href="event?e=123&amp;f=ST">Event</a>
    <a href="?e=123&amp;d=456&amp;f=ST">Deck</a>
    """
    assert tournament_urls_from_html(event_html) == [f"{BASE}/event?e=123&f=ST"]
    found_deck = deck_links_from_html(event_html)[0]
    assert found_deck[0] == "456"
    assert found_deck[2] == f"{BASE}/event?e=123&d=456&f=ST"

    deck_html = '<a href="mtgo?d=456&amp;f=Standard_Test">MTGO</a>'
    assert export_url_from_html(deck_html, "456").startswith(f"{BASE}/mtgo?d=456")

    CARD_CACHE.clear()
    mock_card = {
        "name": "Bala Ged Recovery // Bala Ged Sanctuary",
        "card_faces": [{"name": "Bala Ged Recovery"}, {"name": "Bala Ged Sanctuary"}],
    }
    cache_card(mock_card)
    assert CARD_CACHE["bala ged recovery"] is mock_card
    print("SELF-TEST OK", flush=True)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        instance_lock = acquire_instance_lock()
        if instance_lock is None:
            print("Ya hay otra ejecución de MTGTop8 abierta. Ciérrala antes de continuar.")
        else:
            try:
                old_stdout = sys.stdout
                with open(LOG, "w", encoding="utf-8") as log_file:
                    sys.stdout = Tee(old_stdout, log_file)
                    try:
                        run()
                    except Exception as error:
                        print("ERROR GLOBAL", repr(error), flush=True)
                    finally:
                        print("LOG", LOG, flush=True)
                        sys.stdout = old_stdout
            finally:
                release_instance_lock(instance_lock)
