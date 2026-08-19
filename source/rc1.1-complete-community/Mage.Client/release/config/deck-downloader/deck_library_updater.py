#!/usr/bin/env python3
"""Actualizador acumulativo de mazos para XMage.

Ejecuta los conectores instalados, convierte sus resultados al DCK nativo de
XMage y conserva para siempre cada composición distinta. Está diseñado para
ser llamado desde DeckDownloaderPane, aunque también funciona desde consola.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


FORMATS = ("Standard", "Pioneer", "Modern")
SOURCES = ("MTGO", "MTGGoldfish", "MTGTop8")
ROOT = Path(__file__).resolve().parent
CLIENT_ROOT = ROOT.parent.parent
ARCHIVE = CLIENT_ROOT / "sample-decks" / "Descargados"
ARCHIVE_LOG_PATH = ARCHIVE / "registro-general-decks.log"
STATE_PATH = ROOT / "deck-library-state.json"
SCRYFALL_CACHE_PATH = ROOT / "scryfall-deck-library-cache.json"
LOG_PATH = ROOT / "deck-library-updater.log"
CANCEL_PATH = ROOT / ".cancel-update"
LAST_REQUEST = 0.0
UPDATER_VERSION = "Decks V2.2 - 2026-08-11"


def configure_utf8_stdio():
    """Evita que la consola CP-1252 de Windows rompa una actualización."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


configure_utf8_stdio()


class UpdateCancelled(Exception):
    pass


def timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def initialize_logs(archive=ARCHIVE):
    """Crea los registros visibles antes de iniciar cualquier conexión."""
    archive.mkdir(parents=True, exist_ok=True)
    root_log = archive / "registro-general-decks.log"
    with root_log.open("a", encoding="utf-8") as output:
        output.write(f"\n[{timestamp()}] INICIO | motor={UPDATER_VERSION}\n")
    for fmt in FORMATS:
        folder = archive / fmt
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / "registro-importaciones.log").open("a", encoding="utf-8") as output:
            output.write(f"[{timestamp()}] INICIO | motor={UPDATER_VERSION}\n")
    return root_log


def check_cancelled():
    if CANCEL_PATH.exists():
        raise UpdateCancelled()


def interruptible_sleep(seconds):
    deadline = time.monotonic() + max(0.0, float(seconds))
    while True:
        check_cancelled()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(0.2, remaining))


def append_format_log(fmt, message):
    folder = ARCHIVE / fmt
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "registro-importaciones.log").open("a", encoding="utf-8") as output:
        output.write(f"[{timestamp()}] {message}\n")


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


def load_json(path, default):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except Exception:
        return default


def save_json_atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


STATE = load_json(STATE_PATH, {"version": 1, "decks": {}})
if not isinstance(STATE, dict) or not isinstance(STATE.get("decks"), dict):
    STATE = {"version": 1, "decks": {}}
SCRYFALL_CACHE = load_json(SCRYFALL_CACHE_PATH, {})
if not isinstance(SCRYFALL_CACHE, dict):
    SCRYFALL_CACHE = {}


def parse_rows(path):
    main, side = [], []
    is_side = False
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            if main:
                is_side = True
            continue
        if line in {"LAYOUT MAIN", "LAYOUT SIDEBOARD"}:
            continue
        if re.match(r"^(?:sideboard|banquillo)\b", line, re.I):
            is_side = True
            continue
        side_prefix = re.match(r"^SB:\s*", line, re.I)
        if side_prefix:
            is_side = True
            line = line[side_prefix.end():]
        match = re.match(r"^(\d+)\s+(?:\[[^]]+\]\s+)?(.+?)\s*$", line)
        if not match:
            continue
        quantity = int(match.group(1))
        name = match.group(2).strip()
        (side if is_side else main).append((quantity, name))
    return merge_rows(main), merge_rows(side)


def merge_rows(rows):
    merged = {}
    shown = {}
    for quantity, name in rows:
        key = re.sub(r"\s+", " ", name).strip().casefold()
        merged[key] = merged.get(key, 0) + quantity
        shown.setdefault(key, name)
    return [(merged[key], shown[key]) for key in sorted(merged)]


def fingerprint(main, side):
    canonical = {
        "main": sorted((name.casefold(), quantity) for quantity, name in main),
        "side": sorted((name.casefold(), quantity) for quantity, name in side),
    }
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def request_card(name):
    global LAST_REQUEST
    key = name.casefold()
    cached = SCRYFALL_CACHE.get(key)
    if isinstance(cached, dict):
        return cached
    queries = [name]
    if " // " in name:
        queries.append(name.split(" // ", 1)[0].strip())
    for query in queries:
        for mode in ("exact", "fuzzy"):
            delay = 0.12 - (time.monotonic() - LAST_REQUEST)
            if delay > 0:
                interruptible_sleep(delay)
            url = "https://api.scryfall.com/cards/named?" + mode + "=" + urllib.parse.quote(query)
            request = urllib.request.Request(url, headers={
                "User-Agent": "XMage-Deck-Library/1.0",
                "Accept": "application/json",
            })
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    card = json.load(response)
                LAST_REQUEST = time.monotonic()
                if card.get("set") and card.get("collector_number"):
                    result = {
                        "name": card.get("name", name),
                        "set": str(card["set"]).upper(),
                        "number": str(card["collector_number"]),
                        "faces": [face.get("name", "") for face in card.get("card_faces") or []],
                    }
                    for alias in [name, result["name"], *result["faces"]]:
                        if alias:
                            SCRYFALL_CACHE[alias.casefold()] = result
                    return result
            except urllib.error.HTTPError as error:
                LAST_REQUEST = time.monotonic()
                if error.code == 429:
                    # Nunca congelar la pestaña durante 60 segundos. El trabajo
                    # por lotes y la caché resuelven casi todo; un caso suelto
                    # limitado se rechaza y podrá recuperarse en la siguiente ejecución.
                    print("Scryfall limita una consulta individual; se aplaza sin bloquear.", flush=True)
                    return None
                if error.code not in (400, 404):
                    raise
            except Exception:
                LAST_REQUEST = time.monotonic()
    return None


def cache_card(card, requested=None):
    if not isinstance(card, dict) or not card.get("set") or not card.get("collector_number"):
        return
    result = {
        "name": card.get("name", requested or ""),
        "set": str(card["set"]).upper(),
        "number": str(card["collector_number"]),
        "faces": [face.get("name", "") for face in card.get("card_faces") or []],
    }
    for alias in [requested, result["name"], *result["faces"]]:
        if alias:
            SCRYFALL_CACHE[alias.casefold()] = result


def prefetch_cards_bulk(names):
    """Resuelve nombres en lotes de 75; los casos raros quedan para el fallback individual."""
    pending = []
    seen = set()
    for name in names:
        key = name.casefold()
        if key not in SCRYFALL_CACHE and key not in seen:
            seen.add(key)
            pending.append(name)
    if not pending:
        print("Scryfall: todas las cartas estaban en la caché permanente.", flush=True)
        return
    print(f"Scryfall: resolviendo {len(pending)} cartas únicas por lotes...", flush=True)
    for offset in range(0, len(pending), 75):
        check_cancelled()
        batch = pending[offset:offset + 75]
        payload = json.dumps({"identifiers": [{"name": name} for name in batch]}).encode("utf-8")
        request = urllib.request.Request(
            "https://api.scryfall.com/cards/collection",
            data=payload,
            headers={
                "User-Agent": "XMage-Deck-Library/1.1",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    result = json.load(response)
                for card in result.get("data") or []:
                    cache_card(card)
                save_json_atomic(SCRYFALL_CACHE_PATH, SCRYFALL_CACHE)
                print(
                    f"Scryfall lote {offset // 75 + 1}: "
                    f"{min(offset + len(batch), len(pending))}/{len(pending)}",
                    flush=True,
                )
                break
            except urllib.error.HTTPError as error:
                if error.code == 429 and attempt < 2:
                    wait = min(5.0, max(2.0, float(error.headers.get("Retry-After", "0") or 0)))
                    print(f"Scryfall limita el lote; reintento en {wait:.0f} segundos...", flush=True)
                    interruptible_sleep(wait)
                    continue
                print(f"AVISO: lote Scryfall omitido: HTTP {error.code}", flush=True)
                break
            except Exception as error:
                print(f"AVISO: lote Scryfall omitido: {error}", flush=True)
                break
        interruptible_sleep(0.25)


def xmage_name(card, requested):
    requested_key = requested.casefold()
    for face in card.get("faces", []):
        if face.casefold() == requested_key:
            return face
    official = card.get("name", requested)
    return official.split(" // ", 1)[0].strip() if " // " in official else official


def safe_name(value):
    cleaned = re.sub(r"[^A-Za-z0-9 _.-]", "", value).strip()
    return re.sub(r"\s+", "_", cleaned)[:100] or "Deck"


def build_native_dck(main, side):
    lines = []
    missing = []
    for prefix, rows in (("", main), ("SB: ", side)):
        for quantity, requested in rows:
            card = request_card(requested)
            if not card:
                missing.append(requested)
                continue
            lines.append(
                f"{prefix}{quantity} [{card['set']}:{card['number']}] {xmage_name(card, requested)}"
            )
    if missing:
        raise ValueError("Scryfall no encuentra: " + ", ".join(sorted(set(missing))))
    lines.extend(("LAYOUT MAIN", "LAYOUT SIDEBOARD"))
    return "\n".join(lines) + "\n"


def discover_outputs(source):
    base = ROOT / source
    candidates = []
    preferred = base / "XMage_DCK"
    fallback = base / "XMage"
    selected = preferred if preferred.is_dir() else fallback
    for fmt in FORMATS:
        folder = selected / fmt
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.suffix.casefold() in {".dck", ".txt"}:
                candidates.append((fmt, path))
    return candidates


def import_source(source):
    added = duplicate = rejected = 0
    format_stats = {fmt: [0, 0, 0] for fmt in FORMATS}
    stamp = time.strftime("%Y-%m-%d")
    candidates = discover_outputs(source)
    names_to_resolve = []
    for _, path in candidates:
        content = path.read_text(encoding="utf-8-sig", errors="replace")
        if path.suffix.casefold() != ".dck" or "LAYOUT MAIN" not in content:
            main, side = parse_rows(path)
            names_to_resolve.extend(name for _, name in main + side)
    prefetch_cards_bulk(names_to_resolve)
    for fmt, path in candidates:
        check_cancelled()
        try:
            main, side = parse_rows(path)
            counts = (sum(q for q, _ in main), sum(q for q, _ in side))
            if counts != (60, 15):
                raise ValueError(f"tamaño {counts[0]}+{counts[1]}")
            key = f"{fmt}:{fingerprint(main, side)}"
            if key in STATE["decks"]:
                duplicate += 1
                format_stats[fmt][1] += 1
                append_format_log(
                    fmt,
                    f"REPETIDO | fuente={source} | original={path.name} | "
                    f"huella={key.rsplit(':', 1)[-1]} | conservado={STATE['decks'][key].get('file', '')}",
                )
                continue
            content = path.read_text(encoding="utf-8-sig", errors="replace")
            if path.suffix.casefold() != ".dck" or "LAYOUT MAIN" not in content:
                content = build_native_dck(main, side)
            destination_dir = ARCHIVE / fmt
            destination_dir.mkdir(parents=True, exist_ok=True)
            short_hash = key.rsplit(":", 1)[-1][:10]
            destination = destination_dir / f"{stamp}_{source}_{safe_name(path.stem)}_{short_hash}.dck"
            temporary = destination.with_suffix(".dck.tmp")
            temporary.write_text(content, encoding="utf-8", newline="\n")
            os.replace(temporary, destination)
            STATE["decks"][key] = {
                "source": source,
                "format": fmt,
                "imported": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "file": str(destination.relative_to(CLIENT_ROOT)),
                "original": path.name,
            }
            save_json_atomic(STATE_PATH, STATE)
            added += 1
            format_stats[fmt][0] += 1
            append_format_log(
                fmt,
                f"NUEVO | fuente={source} | original={path.name} | "
                f"huella={short_hash} | destino={destination.name} | tamaño=60+15",
            )
            print(f"NUEVO [{fmt}] {destination.name}", flush=True)
        except Exception as error:
            rejected += 1
            format_stats[fmt][2] += 1
            append_format_log(
                fmt,
                f"RECHAZADO | fuente={source} | original={path.name} | motivo={error}",
            )
            print(f"RECHAZADO [{fmt}] {path.name}: {error}", flush=True)
    save_json_atomic(SCRYFALL_CACHE_PATH, SCRYFALL_CACHE)
    print(f"RESUMEN {source}: nuevos={added}, repetidos={duplicate}, rechazados={rejected}", flush=True)
    for fmt in FORMATS:
        fmt_added, fmt_duplicate, fmt_rejected = format_stats[fmt]
        append_format_log(
            fmt,
            f"FIN DE FUENTE | fuente={source} | nuevos={fmt_added} | "
            f"repetidos={fmt_duplicate} | rechazados={fmt_rejected}",
        )
    return added, duplicate, rejected


def run_connector(source):
    scripts = {
        "MTGO": [ROOT / "mtgo_3_formatos_fusionado.py"],
        "MTGGoldfish": [ROOT / "goldfish_3_formatos.py"],
        "MTGTop8": [ROOT / "mtgtop8_3_formatos.py", ROOT / "mtgtop8_a_xmage_dck.py"],
    }
    print(f"\n=== {source}: recuperando resultados de una ejecución anterior ===", flush=True)
    recovered = import_source(source)
    if any(recovered):
        print(
            f"RECUPERACIÓN {source}: nuevos={recovered[0]}, "
            f"repetidos={recovered[1]}, rechazados={recovered[2]}",
            flush=True,
        )
    failures = []
    for script in scripts[source]:
        check_cancelled()
        if not script.is_file():
            raise FileNotFoundError(f"Falta el conector {script.name}")
        print(f"\n=== {source}: ejecutando {script.name} ===", flush=True)
        child_environment = os.environ.copy()
        child_environment["PYTHONUTF8"] = "1"
        child_environment["PYTHONIOENCODING"] = "utf-8:replace"
        child = subprocess.Popen(
            [sys.executable, "-u", str(script)],
            cwd=ROOT,
            env=child_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        lines = queue.Queue()

        def read_child_output():
            try:
                for line in child.stdout:
                    lines.put(line)
            finally:
                lines.put(None)

        reader = threading.Thread(target=read_child_output, daemon=True)
        reader.start()
        output_finished = False
        while child.poll() is None or not output_finished:
            try:
                line = lines.get(timeout=0.25)
                if line is None:
                    output_finished = True
                else:
                    print(line, end="", flush=True)
            except queue.Empty:
                pass
            if CANCEL_PATH.exists():
                print("\nCANCELANDO: deteniendo el conector activo...", flush=True)
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                raise UpdateCancelled()
        reader.join(timeout=1)
        if child.returncode != 0:
            failures.append(f"{script.name}: código {child.returncode}")
            print(
                f"AVISO: {script.name} terminó con error; se importará igualmente "
                "cualquier mazo válido que haya generado.",
                flush=True,
            )
    imported = import_source(source)
    if failures:
        print("AVISO DEL CONECTOR: " + "; ".join(failures), flush=True)
    return tuple(a + b for a, b in zip(recovered, imported))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=(*SOURCES, "all"), default="all")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    CANCEL_PATH.unlink(missing_ok=True)
    selected = SOURCES if args.source == "all" else (args.source,)
    totals = [0, 0, 0]
    for source in selected:
        try:
            result = run_connector(source)
            totals = [a + b for a, b in zip(totals, result)]
        except UpdateCancelled:
            print("\nACTUALIZACIÓN CANCELADA. Los mazos guardados permanecen intactos.", flush=True)
            return
        except Exception as error:
            print(f"ERROR {source}: {error}", flush=True)
    print(
        f"\nACTUALIZACIÓN TERMINADA: nuevos={totals[0]}, "
        f"repetidos={totals[1]}, rechazados={totals[2]}",
        flush=True,
    )


def self_test():
    sample_main = [(4, "Lightning Bolt"), (56, "Mountain")]
    sample_side = [(15, "Island")]
    assert fingerprint(sample_main, sample_side) == fingerprint(list(reversed(sample_main)), sample_side)
    assert sum(q for q, _ in merge_rows(sample_main)) == 60
    assert safe_name("Esper / Control: Test") == "Esper_Control_Test"
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        test_archive = Path(temporary) / "Descargados"
        initialize_logs(test_archive)
        assert (test_archive / "registro-general-decks.log").is_file()
        for fmt in FORMATS:
            assert (test_archive / fmt / "registro-importaciones.log").is_file()
    print("SELF-TEST OK: huellas, cantidades, nombres y registros.")


if __name__ == "__main__":
    old_stdout = sys.stdout
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    initialize_logs()
    with LOG_PATH.open("a", encoding="utf-8") as log_file, \
            ARCHIVE_LOG_PATH.open("a", encoding="utf-8") as archive_log:
        archive_log.write(f"\n===== ACTUALIZACIÓN {timestamp()} =====\n")
        archive_log.flush()
        sys.stdout = Tee(old_stdout, log_file, archive_log)
        try:
            main()
        finally:
            CANCEL_PATH.unlink(missing_ok=True)
            sys.stdout = old_stdout
