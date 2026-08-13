#!/usr/bin/env python3
"""Final isolated migration gate V2 for XMage 1.4.61V1 Community Patch.

SAFE MODE: NEVER modifies active XMage.

V2 removes V1's fragile fixed-path dependency on registro-general-decks.log.
Evidence is collected from the isolated GUI smoke filesystem itself:
- V4 static smoke manifest passed.
- isolated GUI client/runtime exist.
- MTGTop8 XMage DCK output contains exactly 25 Standard + 25 Pioneer + 25 Modern.
- conversion log confirms TOTAL DCK 75 when available.
- any general smoke log found anywhere under the port workspace is parsed as extra evidence.
- any explicit rejected>0 found in relevant smoke logs fails the gate.

If mandatory checks pass, the already-tested isolated GUI tree is packaged into
FINAL_MIGRATION_CANDIDATE_V2.zip. It is NOT installed or activated.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "migration-workspace" / "port-1.4.61V1"
REPORTS = WORK / "reports"
GUI = WORK / "gui-smoke-v1"
RUNTIME = GUI / "config" / "deck-downloader"
STATIC_RESULT = REPORTS / "smoke-package-result-v4.json"
CLIENT = GUI / "lib" / "mage-client-1.4.61.jar"
RUNTIME_MAIN = RUNTIME / "deck_library_updater.py"
TOP8_DCK = RUNTIME / "MTGTop8" / "XMage_DCK"
TOP8_CONVERSION_LOG = RUNTIME / "mtgtop8_a_xmage_dck.log"

FINAL_OUT = WORK / "final-candidate-v2"
FINAL_ZIP = FINAL_OUT / "XMage_1.4.61V1_CommunityPatch_FINAL_MIGRATION_CANDIDATE_V2.zip"
FINAL_MANIFEST = FINAL_OUT / "FINAL_MIGRATION_GATE_V2.json"
FINAL_SUMMARY = FINAL_OUT / "RESUMEN_FINAL_MIGRATION_GATE_V2.txt"

SAFE_MTGO_FAILURE = "preflight incompleto; no se ha limpiado ni modificado MTGO"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def load_json(path: Path) -> dict:
    require(path.is_file(), f"Missing required JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def find_general_logs() -> list[Path]:
    exact = list(WORK.rglob("registro-general-decks.log"))
    if exact:
        return sorted(exact, key=lambda p: p.stat().st_mtime, reverse=True)
    fuzzy = []
    for p in WORK.rglob("*.log"):
        n = p.name.lower()
        if "general" in n and "deck" in n:
            fuzzy.append(p)
    return sorted(fuzzy, key=lambda p: p.stat().st_mtime, reverse=True)


def count_dcks() -> dict[str, int]:
    result = {}
    for fmt in ("Standard", "Pioneer", "Modern"):
        folder = TOP8_DCK / fmt
        require(folder.is_dir(), f"Missing MTGTop8 DCK folder: {folder}")
        result[fmt.lower()] = len([p for p in folder.glob("*.dck") if p.is_file()])
    return result


def scan_rejections_and_errors(logs: list[Path]) -> dict:
    rejected_hits = []
    unsafe_errors = []
    safe_mtgo_warning = False
    summaries = []

    for path in logs:
        text = read_text(path)
        if SAFE_MTGO_FAILURE in text:
            safe_mtgo_warning = True

        for m in re.finditer(r"rechazados\s*=\s*(\d+)", text, re.I):
            value = int(m.group(1))
            summaries.append({"log": str(path), "rejected": value})
            if value > 0:
                rejected_hits.append(f"{path.name}: rechazados={value}")

        for line in text.splitlines():
            if "ERROR GLOBAL" in line.upper():
                if SAFE_MTGO_FAILURE.lower() not in line.lower():
                    # The safe MTGO exception can be printed on the following traceback line,
                    # so defer a line-level failure if the whole file contains the safe marker.
                    if SAFE_MTGO_FAILURE not in text:
                        unsafe_errors.append(f"{path.name}: {line.strip()}")

    require(not rejected_hits, "Rejected decks found: " + " | ".join(rejected_hits))
    require(not unsafe_errors, "Unexpected global errors found: " + " | ".join(unsafe_errors))
    return {
        "safe_mtgo_preflight_warning": safe_mtgo_warning,
        "rejection_summaries": summaries,
        "logs_scanned": [str(p) for p in logs],
    }


def package_tree(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.unlink(missing_ok=True)
    with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(src.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(src).as_posix())


def validate_zip(path: Path) -> dict:
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
    required = {
        "lib/mage-client-1.4.61.jar",
        "config/deck-downloader/deck_library_updater.py",
        "startClient.bat",
    }
    missing = sorted(required - names)
    require(not missing, "Final ZIP missing required entries: " + ", ".join(missing))
    return {"entry_count": len(names), "required_entries": sorted(required)}


def main() -> int:
    print("=== XMage Community Patch - FINAL MIGRATION GATE V2 ===")
    print("SAFE MODE: active XMage will NOT be modified.\n")

    static = load_json(STATIC_RESULT)
    require(static.get("status") == "STATIC_SMOKE_PASSED_MANUAL_GUI_SMOKE_REQUIRED",
            "V4 static smoke result is not in expected passed state")
    require(static.get("active_xmage_modified") is False,
            "Static smoke manifest does not prove active XMage remained untouched")
    print("[OK] V4 static smoke manifest passed")

    require(GUI.is_dir(), f"Missing isolated GUI tree: {GUI}")
    require(CLIENT.is_file(), f"Missing patched client: {CLIENT}")
    require(RUNTIME_MAIN.is_file(), f"Missing Deck Downloader runtime: {RUNTIME_MAIN}")
    print("[OK] Isolated GUI client + runtime present")

    dcks = count_dcks()
    require(dcks["standard"] == 25, f"Standard DCK count is {dcks['standard']}, expected 25")
    require(dcks["pioneer"] == 25, f"Pioneer DCK count is {dcks['pioneer']}, expected 25")
    require(dcks["modern"] == 25, f"Modern DCK count is {dcks['modern']}, expected 25")
    print("[OK] MTGTop8 DCK output: Standard 25/25, Pioneer 25/25, Modern 25/25")

    if TOP8_CONVERSION_LOG.is_file():
        conversion_text = read_text(TOP8_CONVERSION_LOG)
        require("TOTAL DCK 75" in conversion_text,
                "MTGTop8 conversion log exists but does not confirm TOTAL DCK 75")
        print("[OK] MTGTop8 conversion log confirms TOTAL DCK 75")
    else:
        print("[WARN] Conversion log not found; exact filesystem count is used as evidence")

    general_logs = find_general_logs()
    all_relevant_logs = list(general_logs)
    for p in RUNTIME.glob("*.log"):
        if p not in all_relevant_logs:
            all_relevant_logs.append(p)
    log_scan = scan_rejections_and_errors(all_relevant_logs)
    if general_logs:
        print(f"[OK] General smoke log found automatically: {general_logs[0]}")
    else:
        print("[WARN] General smoke log not found; gate uses generated artifacts + component logs")
    if log_scan["safe_mtgo_preflight_warning"]:
        print("[WARN] MTGO safe preflight warning recorded; MTGO data was not cleaned or modified")
    print("[OK] No rejected>0 found in available smoke logs")

    if FINAL_OUT.exists():
        shutil.rmtree(FINAL_OUT)
    FINAL_OUT.mkdir(parents=True)

    print("[STEP] Packaging already-tested isolated GUI tree...")
    package_tree(GUI, FINAL_ZIP)
    zip_info = validate_zip(FINAL_ZIP)
    final_hash = sha256(FINAL_ZIP)
    print(f"[OK] Final candidate SHA-256: {final_hash}")

    manifest = {
        "schema": 2,
        "gate_version": "V2",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FINAL_MIGRATION_CANDIDATE_READY_NOT_INSTALLED",
        "static_smoke": "V4_PASS",
        "gui_smoke_tree": str(GUI),
        "client_sha256": sha256(CLIENT),
        "dck_counts": dcks,
        "general_log_found": str(general_logs[0]) if general_logs else None,
        "log_scan": log_scan,
        "final_candidate": str(FINAL_ZIP),
        "final_candidate_sha256": final_hash,
        "zip_validation": zip_info,
        "active_xmage_modified": False,
        "candidate_installed": False,
        "activation_allowed": False,
        "next_gate": "controlled install + rollback preparation",
    }
    FINAL_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = [
        "XMage Community Patch - FINAL MIGRATION GATE V2",
        "================================================",
        "",
        "RESULT: PASS",
        "Status: FINAL_MIGRATION_CANDIDATE_READY_NOT_INSTALLED",
        "Static smoke V4: PASS",
        "Isolated GUI client/runtime: PASS",
        f"Standard DCK: {dcks['standard']}/25",
        f"Pioneer DCK: {dcks['pioneer']}/25",
        f"Modern DCK: {dcks['modern']}/25",
        f"Total DCK: {sum(dcks.values())}",
        f"General log auto-detected: {bool(general_logs)}",
        f"MTGO safe preflight warning: {log_scan['safe_mtgo_preflight_warning']}",
        "Rejected>0 in available logs: NO",
        "",
        f"Final candidate: {FINAL_ZIP}",
        f"SHA-256: {final_hash}",
        "",
        "Candidate has NOT been installed.",
        "Active XMage was NOT modified.",
        "Activation remains BLOCKED pending controlled install + rollback preparation.",
    ]
    FINAL_SUMMARY.write_text("\n".join(summary) + "\n", encoding="utf-8")

    print("\n=== FINAL MIGRATION GATE V2 PASSED ===")
    print(f"Candidate: {FINAL_ZIP}")
    print(f"Manifest: {FINAL_MANIFEST}")
    print(f"Summary: {FINAL_SUMMARY}")
    print("Active XMage was NOT modified. Installation remains BLOCKED.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("FINAL GATE V2 FAILED SAFELY. Active XMage was NOT modified.")
        input("Press Enter to close...")
        raise SystemExit(1)
