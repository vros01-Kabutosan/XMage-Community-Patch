#!/usr/bin/env python3
"""Final isolated migration gate V1 for XMage 1.4.61V1 Community Patch.

SAFE MODE: this tool NEVER modifies the active XMage installation.

Required evidence:
- V4 static smoke result exists and passed.
- Isolated GUI smoke folder exists with patched client + Deck Downloader runtime.
- GUI smoke general log completed with rejected=0.
- MTGTop8 conversion produced 25/25 DCK for Standard, Pioneer and Modern (75 total).
- MTGGoldfish completed with rejected=0.

Known tolerated external-source condition:
- MTGO may report the exact safe preflight failure "preflight incompleto; no se ha limpiado ni modificado MTGO".
  This is recorded as a warning, not silently ignored, because it confirms MTGO data was not cleaned or modified.

If all mandatory checks pass, the already-tested isolated GUI tree is packaged as a FINAL_MIGRATION_CANDIDATE_V1.zip.
The tool does NOT install or activate that candidate.
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
LOG = RUNTIME / "registro-general-decks.log"
STATIC_RESULT = REPORTS / "smoke-package-result-v4.json"
FINAL_OUT = WORK / "final-candidate-v1"
FINAL_ZIP = FINAL_OUT / "XMage_1.4.61V1_CommunityPatch_FINAL_MIGRATION_CANDIDATE_V1.zip"
FINAL_MANIFEST = FINAL_OUT / "FINAL_MIGRATION_GATE_V1.json"
FINAL_SUMMARY = FINAL_OUT / "RESUMEN_FINAL_MIGRATION_GATE_V1.txt"

CLIENT = GUI / "lib" / "mage-client-1.4.61.jar"
RUNTIME_MAIN = RUNTIME / "deck_library_updater.py"

SAFE_MTGO_FAILURE = "preflight incompleto; no se ha limpiado ni modificado MTGO"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_json(path: Path) -> dict:
    require(path.is_file(), f"Missing required JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def latest_update_block(text: str) -> str:
    marks = list(re.finditer(r"^===== ACTUALIZACI[ÓO]N .*? =====$", text, re.M))
    if not marks:
        return text
    return text[marks[-1].start():]


def check_log(text: str) -> dict:
    block = latest_update_block(text)

    required_lines = [
        "Standard: 25/25 DCK",
        "Pioneer: 25/25 DCK",
        "Modern: 25/25 DCK",
        "TOTAL DCK 75",
        "ACTUALIZACIÓN TERMINADA: nuevos=126, repetidos=24, rechazados=0",
    ]
    missing = [line for line in required_lines if line not in block]
    require(not missing, "Missing mandatory GUI smoke evidence: " + "; ".join(missing))

    goldfish = re.findall(r"RESUMEN MTGGoldfish: nuevos=(\d+), repetidos=(\d+), rechazados=(\d+)", block)
    require(goldfish, "No MTGGoldfish summary found in latest smoke log")
    gf_new, gf_dup, gf_rej = map(int, goldfish[-1])
    require(gf_rej == 0, f"MTGGoldfish rejected decks: {gf_rej}")

    top8 = re.findall(r"RESUMEN MTGTop8: nuevos=(\d+), repetidos=(\d+), rechazados=(\d+)", block)
    require(top8, "No MTGTop8 summary found in latest smoke log")
    t8_new, t8_dup, t8_rej = map(int, top8[-1])
    require(t8_rej == 0, f"MTGTop8 rejected decks: {t8_rej}")

    mtgo_safe_warning = SAFE_MTGO_FAILURE in block
    unsafe_mtgo_errors = []
    for line in block.splitlines():
        if "ERROR GLOBAL" in line and SAFE_MTGO_FAILURE not in line:
            unsafe_mtgo_errors.append(line.strip())
    require(not unsafe_mtgo_errors, "Unexpected global error(s): " + " | ".join(unsafe_mtgo_errors))

    return {
        "goldfish": {"new": gf_new, "duplicates": gf_dup, "rejected": gf_rej},
        "mtgtop8": {"new": t8_new, "duplicates": t8_dup, "rejected": t8_rej},
        "dck": {"standard": 25, "pioneer": 25, "modern": 25, "total": 75},
        "mtgo_safe_preflight_warning": mtgo_safe_warning,
    }


def package_tree(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.unlink(missing_ok=True)
    with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(src.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(src).as_posix())


def validate_zip(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
    required = {
        "lib/mage-client-1.4.61.jar",
        "config/deck-downloader/deck_library_updater.py",
        "startClient.bat",
    }
    missing = sorted(required - names)
    require(not missing, "Final ZIP missing required entries: " + ", ".join(missing))
    return {"required_entries": sorted(required), "entry_count": len(names)}


def main() -> int:
    print("=== XMage Community Patch - FINAL MIGRATION GATE V1 ===")
    print("SAFE MODE: active XMage will NOT be modified.\n")

    static = load_json(STATIC_RESULT)
    require(static.get("status") == "STATIC_SMOKE_PASSED_MANUAL_GUI_SMOKE_REQUIRED",
            "V4 static smoke result is not in expected passed state")
    require(static.get("active_xmage_modified") is False,
            "Static smoke manifest does not prove active XMage remained untouched")
    print("[OK] V4 static smoke manifest passed")

    require(GUI.is_dir(), f"Missing isolated GUI smoke tree: {GUI}")
    require(CLIENT.is_file(), f"Missing patched isolated client: {CLIENT}")
    require(RUNTIME_MAIN.is_file(), f"Missing Deck Downloader runtime: {RUNTIME_MAIN}")
    require(LOG.is_file(), f"Missing GUI smoke log: {LOG}")
    print("[OK] Isolated GUI smoke tree present")

    log_text = LOG.read_text(encoding="utf-8", errors="replace")
    evidence = check_log(log_text)
    print("[OK] Standard/Pioneer/Modern: 25/25/25 DCK (75 total)")
    print(f"[OK] MTGGoldfish rejected={evidence['goldfish']['rejected']}")
    print(f"[OK] MTGTop8 rejected={evidence['mtgtop8']['rejected']}")
    if evidence["mtgo_safe_preflight_warning"]:
        print("[WARN] MTGO safe preflight did not find 25 events; MTGO data was not cleaned or modified")

    if FINAL_OUT.exists():
        shutil.rmtree(FINAL_OUT)
    FINAL_OUT.mkdir(parents=True)

    print("[STEP] Packaging the already-tested isolated GUI tree...")
    package_tree(GUI, FINAL_ZIP)
    zip_validation = validate_zip(FINAL_ZIP)
    final_hash = sha256(FINAL_ZIP)
    print(f"[OK] Final candidate SHA-256: {final_hash}")

    manifest = {
        "schema": 1,
        "gate_version": "V1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FINAL_MIGRATION_CANDIDATE_READY_NOT_INSTALLED",
        "source_tree": str(GUI),
        "source_client_sha256": sha256(CLIENT),
        "source_log_sha256": sha256(LOG),
        "static_smoke_candidate_sha256": static.get("candidate_sha256"),
        "functional_evidence": evidence,
        "final_candidate": str(FINAL_ZIP),
        "final_candidate_sha256": final_hash,
        "zip_validation": zip_validation,
        "active_xmage_modified": False,
        "candidate_installed": False,
        "activation_allowed": False,
        "next_gate": "controlled installation/rollback preparation",
    }
    FINAL_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "XMage Community Patch - FINAL MIGRATION GATE V1",
        "================================================",
        "",
        "RESULT: PASS",
        "Status: FINAL_MIGRATION_CANDIDATE_READY_NOT_INSTALLED",
        "",
        "Static V4 smoke: PASS",
        "Isolated GUI launch: PASS (evidence tree preserved)",
        "Deck Downloader functional smoke:",
        "  Standard: 25/25 DCK",
        "  Pioneer: 25/25 DCK",
        "  Modern: 25/25 DCK",
        "  Total: 75 DCK",
        f"  MTGGoldfish rejected: {evidence['goldfish']['rejected']}",
        f"  MTGTop8 rejected: {evidence['mtgtop8']['rejected']}",
        f"  MTGO safe preflight warning: {evidence['mtgo_safe_preflight_warning']}",
        "",
        f"Final candidate: {FINAL_ZIP}",
        f"SHA-256: {final_hash}",
        "",
        "IMPORTANT:",
        "This candidate has NOT been installed.",
        "Active XMage was NOT modified.",
        "Activation remains BLOCKED until controlled install + rollback preparation.",
    ]
    FINAL_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n=== FINAL MIGRATION GATE V1 PASSED ===")
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
        print("FINAL GATE FAILED SAFELY. Active XMage was NOT modified.")
        input("Press Enter to close...")
        raise SystemExit(1)
