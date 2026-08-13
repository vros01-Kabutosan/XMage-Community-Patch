#!/usr/bin/env python3
"""XMage Community Patch - BACKUP + ROLLBACK GATE V4.

SAFE MODE: never activates or overwrites XMage.
V4 builds on V3 discovery but filters archival/staging/candidate copies and
prioritizes a clean active path such as .../xmage/mage-client.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import time
from pathlib import Path

import backup_rollback_gate_v3 as v3

VERSION = "V4"
WORK = v3.WORK
CONTROL = v3.CONTROL
PREP = v3.PREP
OUT = WORK / "backup-rollback-gate-v4"
BACKUPS = OUT / "backups"
REPORT = OUT / "BACKUP_ROLLBACK_GATE_V4.json"
SUMMARY = OUT / "RESUMEN_BACKUP_ROLLBACK_GATE_V4.txt"

NEGATIVE_MARKERS = (
    "backup", "copia", "copias-seguridad", "copias_seguridad", "archive", "archivos",
    "staging", "release_candidate", "release-candidate", "candidate", "no_publicar",
    "no-publicar", "old", "antigu", "test", "prueba"
)


def classify_path(root: Path, meta: dict) -> dict:
    s = str(root).lower().replace("/", "\\")
    score = int(meta.get("score", 0))
    reasons = []

    for marker in NEGATIVE_MARKERS:
        if marker in s:
            score -= 100
            reasons.append(f"archive/staging marker: {marker}")

    # Strong preference for the clean launcher-managed XMage layout visible on this machine.
    if re.search(r"\\xmage\\mage-client$", s):
        score += 80
        reasons.append("clean xmage\\mage-client root")
    elif s.endswith("\\mage-client"):
        score += 20
        reasons.append("mage-client root")

    # Extra confidence when expected active structure exists.
    lib = root / "lib"
    if lib.is_dir() and any(lib.glob("mage-client*.jar")):
        score += 20
        reasons.append("client jar present")
    if any((root / n).is_file() for n in v3.LAUNCHERS):
        score += 20
        reasons.append("client launcher present")
    if (root / "config").is_dir():
        score += 10
        reasons.append("config present")

    return {"root": root, "base_score": meta.get("score", 0), "score": score,
            "reasons": reasons, "hints": meta.get("hints", [])}


def choose_filtered(candidates: dict[Path, dict]) -> dict:
    ranked = [classify_path(root, meta) for root, meta in candidates.items()]
    ranked.sort(key=lambda x: x["score"], reverse=True)

    print(f"[INFO] XMage candidates before filtering: {len(ranked)}")
    for i, item in enumerate(ranked, 1):
        print(f"  {i}. score={item['score']} base={item['base_score']}  {item['root']}")

    viable = [x for x in ranked if x["score"] > 0]
    print(f"[INFO] Viable candidates after archive/staging filtering: {len(viable)}")
    require = v3.require
    require(viable, "No viable active XMage remains after filtering. Nothing was modified.")

    if len(viable) == 1:
        return viable[0]

    top, second = viable[0], viable[1]
    require(
        top["score"] >= 100 and top["score"] >= second["score"] + 40,
        "More than one plausible non-archive XMage remains. Gate stopped safely.",
    )
    print("[OK] One candidate is dominant after clean-path filtering")
    return top


def main() -> int:
    print("=== XMage Community Patch - BACKUP + ROLLBACK GATE V4 ===")
    print("SAFE MODE: candidate activation remains BLOCKED. Detection is read-only.\n")

    v3.require(PREP.is_file(), f"Missing controlled-install manifest: {PREP}")
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    v3.require(prep.get("status") == "CONTROLLED_INSTALL_READY_NOT_ACTIVATED",
               "Controlled Install Prep V1 is not ready")
    v3.require(prep.get("active_xmage_modified") is False,
               "Previous gate does not prove active XMage untouched")
    v3.require(prep.get("activation_allowed") is False,
               "Unexpected activation permission in previous gate")
    print("[OK] Controlled Install Prep V1 safety state verified")

    print("[STEP 1/3] Collecting process + filesystem evidence...")
    process = v3.powershell_process_hints()
    files = v3.filesystem_hints()
    print(f"[INFO] Process path hints: {len(process)}")
    print(f"[INFO] Filesystem path hints: {len(files)}")

    candidates = v3.roots_from_hints(process + files)
    chosen = choose_filtered(candidates)
    active = chosen["root"]
    print(f"[OK] Resolved active XMage root: {active}")
    print(f"[OK] Final detection score: {chosen['score']}")
    for reason in chosen["reasons"]:
        print(f"     - {reason}")

    OUT.mkdir(parents=True, exist_ok=True)
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = BACKUPS / f"XMage_ACTIVE_BACKUP_V4_{stamp}"

    print("[STEP 2/3] Creating full backup (activation still BLOCKED)...")
    shutil.copytree(active, backup, copy_function=shutil.copy2)

    print("[STEP 3/3] Verifying source and backup SHA-256 trees...")
    src_hash, src_count, src_bytes = v3.tree_digest(active)
    dst_hash, dst_count, dst_bytes = v3.tree_digest(backup)
    v3.require((src_hash, src_count, src_bytes) == (dst_hash, dst_count, dst_bytes),
               "Backup verification FAILED")
    print(f"[OK] Verified backup: {src_count} files, {src_bytes} bytes")
    print(f"[OK] Tree SHA-256: {src_hash}")

    rollback = OUT / "ROLLBACK_ACTIVE_XMAGE_V4.cmd"
    rollback.write_text(
        "@echo off\r\nsetlocal\r\n"
        "echo ============================================================\r\n"
        "echo XMage Community Patch - ROLLBACK ACTIVE XMAGE V4\r\n"
        "echo ============================================================\r\n"
        "echo VERIFIED BACKUP EXISTS. AUTOMATIC RESTORE IS NOT ARMED YET.\r\n"
        f"echo Active: {active}\r\n"
        f"echo Backup: {backup}\r\n"
        "echo Nothing is being restored or activated now.\r\n"
        "pause\r\n",
        encoding="utf-8",
    )

    data = {
        "schema": 4,
        "phase": "BACKUP_ROLLBACK_GATE_V4",
        "status": "VERIFIED_BACKUP_READY_ACTIVATION_STILL_BLOCKED",
        "active_xmage": str(active),
        "base_detection_score": chosen["base_score"],
        "final_detection_score": chosen["score"],
        "selection_reasons": chosen["reasons"],
        "detection_hints": chosen["hints"],
        "backup": str(backup),
        "tree_sha256": src_hash,
        "files": src_count,
        "bytes": src_bytes,
        "backup_verified": True,
        "rollback_script": str(rollback),
        "rollback_armed": False,
        "candidate_activated": False,
        "active_xmage_modified_by_gate": False,
        "activation_allowed": False,
        "next_gate": "controlled activation preflight with armed rollback",
    }
    REPORT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    SUMMARY.write_text(
        "XMage Community Patch - BACKUP + ROLLBACK GATE V4\n"
        "==================================================\n\n"
        "RESULT: PASS\n"
        f"Active XMage: {active}\n"
        f"Final detection score: {chosen['score']}\n"
        f"Verified backup: {backup}\n"
        f"Files: {src_count}\nBytes: {src_bytes}\nTree SHA-256: {src_hash}\n"
        "Backup verification: PASS\nRollback: PREPARED, NOT ARMED\n"
        "Candidate activation: BLOCKED\nActive XMage was NOT modified by this gate.\n",
        encoding="utf-8",
    )

    print("\n=== BACKUP + ROLLBACK GATE V4 PASSED ===")
    print(f"Active XMage: {active}")
    print(f"Backup: {backup}")
    print(f"Manifest: {REPORT}")
    print("Candidate activation remains BLOCKED. Active XMage was NOT modified by this gate.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("BACKUP + ROLLBACK GATE V4 STOPPED SAFELY. Candidate was NOT activated.")
        input("Press Enter to close...")
        raise SystemExit(1)
