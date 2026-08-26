#!/usr/bin/env python3
"""Convierte los TXT de MTGTop8 al DCK nativo de XMage.

Clon adaptado del conversor Goldfish de referencia. No modifica el descargador,
los TXT de XMage ni los DCK de Forge. Solo recrea ``MTGTop8/XMage_DCK``.
"""

import json
import os
import re
import shutil
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request


HERE = os.path.dirname(os.path.abspath(__file__))
FORMATS = ("Standard", "Pioneer", "Modern")


def count_source_txt(root):
    total = 0
    for fmt in FORMATS:
        folder = os.path.join(root, "XMage", fmt)
        if not os.path.isdir(folder):
            continue
        total += sum(name.lower().endswith(".txt") for name in os.listdir(folder))
    return total


def detect_root(base=HERE):
    """Prioriza la carpeta MTGTop8 creada por el descargador.

    También admite que este conversor se coloque dentro de MTGTop8. Si existen
    ambas estructuras, escoge la que contenga más TXT; en empate gana MTGTop8.
    """
    nested = os.path.join(base, "MTGTop8")
    candidates = (nested, base)
    return max(candidates, key=lambda path: (count_source_txt(path), path == nested))


ROOT = detect_root()
SOURCE = os.path.join(ROOT, "XMage")
DEST = os.path.join(ROOT, "XMage_DCK")
CACHE_PATH = os.path.join(HERE, "scryfall_mtgtop8_cache.json")
LOG_PATH = os.path.join(HERE, "mtgtop8_a_xmage_dck.log")
HEADERS = {
    "User-Agent": "MTGTop8-XMage-Converter/1.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
}
LAST_REQUEST = 0.0
MIN_INTERVAL = 0.55
LOCKOUT_429 = 5.0


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


try:
    with open(CACHE_PATH, encoding="utf-8") as cache_file:
        CACHE = json.load(cache_file)
except Exception:
    CACHE = {}


def parse_txt(path):
    main = []
    side = []
    is_side = False
    with open(path, encoding="utf-8-sig", errors="replace") as source:
        for raw in source:
            line = raw.strip()
            if not line:
                if main:
                    is_side = True
                continue
            if re.match(r"^(?:sideboard|banquillo)\b", line, re.I):
                is_side = True
                continue
            match = re.match(r"^(\d+)\s+(.+?)\s*$", line)
            if not match:
                continue
            target = side if is_side else main
            target.append((int(match.group(1)), match.group(2).strip()))
    return main, side


def wait_for_api():
    delay = MIN_INTERVAL - (time.monotonic() - LAST_REQUEST)
    if delay > 0:
        time.sleep(delay)


def retry_after(error):
    try:
        server_wait = float(error.headers.get("Retry-After", "0"))
    except (AttributeError, TypeError, ValueError):
        server_wait = 0.0
    return max(LOCKOUT_429, server_wait)


def request_json(url, payload=None, missing_is_ok=False):
    global LAST_REQUEST
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    for attempt in range(5):
        wait_for_api()
        try:
            request = urllib.request.Request(url, data=data, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.load(response)
            LAST_REQUEST = time.monotonic()
            return result
        except urllib.error.HTTPError as error:
            LAST_REQUEST = time.monotonic()
            if error.code in (400, 404) and missing_is_ok:
                return None
            if error.code == 429:
                wait = retry_after(error)
                print(f"SCRYFALL 429: pausa obligatoria de {wait:.0f} s", flush=True)
                time.sleep(wait)
            elif attempt < 4:
                time.sleep(2 + attempt)
            else:
                raise
        except Exception:
            LAST_REQUEST = time.monotonic()
            if attempt == 4:
                raise
            time.sleep(2 + attempt)
    return None


def card_result(card):
    if not card or not card.get("set") or not card.get("collector_number"):
        return None
    return [str(card["set"]).upper(), str(card["collector_number"])]


def cache_card(card, *aliases):
    result = card_result(card)
    if result is None:
        return
    names = [card.get("name", ""), *aliases]
    names.extend(face.get("name", "") for face in (card.get("card_faces") or []))
    for name in names:
        if name:
            CACHE[name.casefold()] = result


def prefetch_cards(names):
    pending = []
    seen = set()
    for name in names:
        key = name.casefold()
        if key not in CACHE and key not in seen:
            seen.add(key)
            pending.append(name)

    for start in range(0, len(pending), 75):
        batch = pending[start:start + 75]
        response = request_json(
            "https://api.scryfall.com/cards/collection",
            {"identifiers": [{"name": name} for name in batch]},
        )
        cards = (response or {}).get("data", [])
        for card in cards:
            cache_card(card)
        print(f"SCRYFALL LOTE {min(start + len(batch), len(pending))}/{len(pending)}", flush=True)


def scryfall_lookup(name):
    key = name.casefold()
    if key in CACHE:
        return CACHE[key]

    queries = [name]
    if " // " in name:
        queries.append(name.split(" // ", 1)[0].strip())
    for query in queries:
        for mode in ("exact", "fuzzy"):
            url = "https://api.scryfall.com/cards/named?" + mode + "=" + urllib.parse.quote(query)
            card = request_json(url, missing_is_ok=True)
            if card:
                cache_card(card, name, query)
                return CACHE.get(key)
    print("  NO ENCONTRADA", name, flush=True)
    return None


def clean_dest():
    if os.path.isdir(DEST):
        shutil.rmtree(DEST)
    os.makedirs(DEST, exist_ok=True)
    print("LIMPIANDO SOLO", DEST, flush=True)


def safe_name(path):
    return re.sub(r"[^A-Za-z0-9_. -]", "", os.path.basename(path)).replace(" ", "_")


def write_dck(path, main, side, resolved_main, resolved_side):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as output:
        for (quantity, name), (set_code, number) in zip(main, resolved_main):
            shown = name.split(" // ", 1)[0].strip() if " // " in name else name
            output.write(f"{quantity} [{set_code}:{number}] {shown}\n")
        for (quantity, name), (set_code, number) in zip(side, resolved_side):
            shown = name.split(" // ", 1)[0].strip() if " // " in name else name
            output.write(f"SB: {quantity} [{set_code}:{number}] {shown}\n")
        output.write("LAYOUT MAIN\nLAYOUT SIDEBOARD\n")
    os.replace(temp, path)


def verify_dck(path):
    main = 0
    side = 0
    with open(path, encoding="utf-8") as source:
        text = source.read()
    for line in text.splitlines():
        side_match = re.match(r"^SB:\s*(\d+)\s+\[[^]]+\]\s+.+$", line)
        main_match = re.match(r"^(\d+)\s+\[[^]]+\]\s+.+$", line)
        if side_match:
            side += int(side_match.group(1))
        elif main_match:
            main += int(main_match.group(1))
    if (main, side) != (60, 15):
        raise ValueError(f"DCK generado incorrectamente: {main}+{side}")
    if "LAYOUT MAIN\nLAYOUT SIDEBOARD\n" not in text:
        raise ValueError("faltan las líneas LAYOUT de XMage")


def find_txt_files():
    files = []
    for fmt in FORMATS:
        source_dir = os.path.join(SOURCE, fmt)
        if not os.path.isdir(source_dir):
            continue
        for name in sorted(os.listdir(source_dir)):
            if name.lower().endswith(".txt"):
                files.append((fmt, os.path.join(source_dir, name)))
    return files


def convert():
    if not os.path.isdir(SOURCE):
        raise FileNotFoundError(f"No existe la carpeta: {SOURCE}")
    files = find_txt_files()
    print("ORIGEN", SOURCE, flush=True)
    print("DESTINO", DEST, flush=True)
    print("TXT ENCONTRADOS", len(files), flush=True)
    if not files:
        raise FileNotFoundError(
            "No se encontró ningún TXT. Ejecuta primero mtgtop8_3_formatos.py; "
            "por seguridad no se ha limpiado XMage_DCK."
        )
    if len(files) != 75:
        print(f"AVISO: se esperaban 75 TXT y se encontraron {len(files)}", flush=True)

    parsed = []
    all_names = []
    for fmt, source in files:
        main, side = parse_txt(source)
        parsed.append((fmt, source, main, side))
        all_names.extend(name for _, name in main + side)

    prefetch_cards(all_names)
    clean_dest()
    total = 0
    counts = {fmt: 0 for fmt in FORMATS}
    for fmt, source, main, side in parsed:
        try:
            main_quantity = sum(quantity for quantity, _ in main)
            side_quantity = sum(quantity for quantity, _ in side)
            print(f"[{fmt}] {os.path.basename(source)}: {main_quantity}+{side_quantity}", flush=True)
            if main_quantity != 60 or side_quantity != 15:
                print("  OMITIDO: no es 60+15", flush=True)
                continue

            names = [name for _, name in main + side]
            identifiers = [scryfall_lookup(name) for name in names]
            if any(identifier is None for identifier in identifiers):
                missing = [name for name, identifier in zip(names, identifiers) if identifier is None]
                print("  OMITIDO Scryfall:", ", ".join(missing), flush=True)
                continue

            out_dir = os.path.join(DEST, fmt)
            stem = os.path.splitext(safe_name(source))[0] + ".dck"
            output_path = os.path.join(out_dir, stem)
            write_dck(output_path, main, side, identifiers[:len(main)], identifiers[len(main):])
            verify_dck(output_path)
            total += 1
            counts[fmt] += 1
            print("  OK", output_path, flush=True)
        except Exception as error:
            print("  ERROR", error, flush=True)

    with open(CACHE_PATH, "w", encoding="utf-8") as cache_file:
        json.dump(CACHE, cache_file, ensure_ascii=False, indent=2)
    for fmt in FORMATS:
        print(f"{fmt}: {counts[fmt]}/25 DCK", flush=True)
    print("TOTAL DCK", total, flush=True)


def self_test():
    main = [(4, "Lightning Bolt"), (56, "Mountain")]
    side = [(15, "Island")]
    with tempfile.TemporaryDirectory() as temp_dir:
        txt_path = os.path.join(temp_dir, "test.txt")
        with open(txt_path, "w", encoding="utf-8") as output:
            output.write("4 Lightning Bolt\n56 Mountain\n\n15 Island\n")
        parsed_main, parsed_side = parse_txt(txt_path)
        assert parsed_main == main
        assert parsed_side == side

        dck_path = os.path.join(temp_dir, "test.dck")
        write_dck(dck_path, main, side, [["M10", "146"], ["M21", "312"]], [["M21", "265"]])
        verify_dck(dck_path)

        nested = os.path.join(temp_dir, "MTGTop8", "XMage", "Standard")
        legacy = os.path.join(temp_dir, "XMage", "Standard")
        os.makedirs(nested)
        os.makedirs(legacy)
        with open(os.path.join(nested, "nuevo.txt"), "w", encoding="utf-8") as output:
            output.write("60 Mountain\n\n15 Island\n")
        assert detect_root(temp_dir) == os.path.join(temp_dir, "MTGTop8")
    print("SELF-TEST OK", flush=True)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        old_stdout = sys.stdout
        with open(LOG_PATH, "w", encoding="utf-8") as log_file:
            sys.stdout = Tee(old_stdout, log_file)
            print("INICIO", time.strftime("%Y-%m-%d %H:%M:%S"), flush=True)
            try:
                convert()
            except Exception as error:
                print("ERROR GLOBAL", repr(error), flush=True)
                traceback.print_exc()
            finally:
                print("LOG", LOG_PATH, flush=True)
                sys.stdout = old_stdout
