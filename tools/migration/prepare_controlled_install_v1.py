#!/usr/bin/env python3
"""Prepare a controlled XMage 1.4.61V1 Community Patch install candidate.

VERSION: V1
SAFE MODE: NEVER modifies the active XMage installation.

This phase:
- verifies the final migration candidate V2 by SHA-256 against its manifest;
- extracts it to an isolated controlled-install-v1 folder;
- validates client, launchers, server artifacts (if present), and Deck Downloader runtime;
- writes PREPARE_BACKUP_V1.cmd and ROLLBACK_V1.cmd templates into the isolated folder;
- writes a manifest/summary with activation_allowed=false.

It deliberately does NOT run backup, rollback, install, activation, or overwrite commands.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "migration-workspace" / "port-1.4.61V1"
FINAL_DIR = WORK / "final-candidate-v2"
FINAL_ZIP = FINAL_DIR / "XMage_1.4.61V1_CommunityPatch_FINAL_MIGRATION_CANDIDATE_V2.zip"
FINAL_MANIFEST = FINAL_DIR / "FINAL_MIGRATION_GATE_V2.json"
CONTROL = WORK / "controlled-install-v1"
INSTALL = CONTROL / "installation"
REPORT = CONTROL / "CONTROLLED_INSTALL_PREP_V1.json"
SUMMARY = CONTROL / "RESUMEN_CONTROLLED_INSTALL_PREP_V1.txt"

CLIENT = Path("lib/mage-client-1.4.61.jar")
RUNTIME = Path("config/deck-downloader/deck_library_updater.py")
CLIENT_LAUNCHER = Path("startClient.bat")
SERVER_LAUNCHER_CANDIDATES = [Path("startServer.bat"), Path("startServerWin7.bat")]


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
    require(path.is_file(), f"Missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_safety_scripts() -> tuple[Path, Path]:
    backup = CONTROL / "PREPARE_BACKUP_V1.cmd"
    rollback = CONTROL / "ROLLBACK_V1.cmd"

    backup.write_text(
        "@echo off\r\n"
        "echo ============================================================\r\n"
        "echo XMage Community Patch - PREPARE BACKUP V1\r\n"
        "echo ============================================================\r\n"
        "echo.\r\n"
        "echo SAFETY TEMPLATE ONLY.\r\n"
        "echo This script is intentionally NOT armed yet.\r\n"
        "echo The active XMage path must be detected and verified by the next gate.\r\n"
        "echo Nothing has been copied or modified.\r\n"
        "echo.\r\n"
        "pause\r\n",
        encoding="utf-8",
    )

    rollback.write_text(
        "@echo off\r\n"
        "echo ============================================================\r\n"
        "echo XMage Community Patch - ROLLBACK V1\r\n"
        "echo ============================================================\r\n"
        "echo.\r\n"
        "echo SAFETY TEMPLATE ONLY.\r\n"
        "echo This rollback is intentionally NOT armed yet.\r\n"
        "echo A verified backup path and active XMage path are required first.\r\n"
        "echo Nothing has been restored or modified.\r\n"
        "echo.\r\n"
        "pause\r\n",
        encoding="utf-8",
    )
    return backup, rollback


def main() -> int:
    print("=== XMage Community Patch - CONTROLLED INSTALL PREP V1 ===")
    print("SAFE MODE: active XMage will NOT be modified.\n")

    gate = load_json(FINAL_MANIFEST)
    require(gate.get("status") == "FINAL_MIGRATION_CANDIDATE_READY_NOT_INSTALLED",
            "Final migration V2 manifest is not in READY_NOT_INSTALLED state")
    require(gate.get("active_xmage_modified") is False,
            "Final migration V2 manifest does not prove active XMage remained untouched")
    expected = gate.get("final_candidate_sha256")
    require(isinstance(expected, str) and len(expected) == 64,
            "Final migration V2 manifest has no valid candidate SHA-256")
    require(FINAL_ZIP.is_file(), f"Missing final candidate: {FINAL_ZIP}")

    actual = sha256(FINAL_ZIP)
    require(actual.lower() == expected.lower(),
            f"Final candidate SHA-256 mismatch: expected {expected}, got {actual}")
    print(f"[OK] Final candidate V2 SHA-256 verified: {actual}")

    if CONTROL.exists():
        shutil.rmtree(CONTROL)
    INSTALL.mkdir(parents=True)

    print("[STEP] Extracting to isolated controlled-install-v1...")
    with zipfile.ZipFile(FINAL_ZIP) as zf:
        zf.extractall(INSTALL)

    require((INSTALL / CLIENT).is_file(), f"Missing client: {CLIENT}")
    require((INSTALL / RUNTIME).is_file(), f"Missing Deck Downloader runtime: {RUNTIME}")
    require((INSTALL / CLIENT_LAUNCHER).is_file(), f"Missing client launcher: {CLIENT_LAUNCHER}")
    print("[OK] Client + Deck Downloader runtime + client launcher present")

    server_launchers = [p.as_posix() for p in SERVER_LAUNCHER_CANDIDATES if (INSTALL / p).is_file()]
    server_jars = [p.relative_to(INSTALL).as_posix() for p in INSTALL.rglob("mage-server*.jar")]
    if server_launchers or server_jars:
        print(f"[OK] Server artifacts detected: launchers={len(server_launchers)}, jars={len(server_jars)}")
    else:
        print("[WARN] No server artifact detected in client candidate; controlled client install remains valid")

    backup, rollback = write_safety_scripts()
    print(f"[OK] Backup template prepared: {backup.name}")
    print(f"[OK] Rollback template prepared: {rollback.name}")

    manifest = {
        "schema": 1,
        "phase": "CONTROLLED_INSTALL_PREP_V1",
        "status": "CONTROLLED_INSTALL_READY_NOT_ACTIVATED",
        "source_candidate": str(FINAL_ZIP),
        "source_candidate_sha256": actual,
        "installation_root": str(INSTALL),
        "client": CLIENT.as_posix(),
        "client_sha256": sha256(INSTALL / CLIENT),
        "runtime": RUNTIME.as_posix(),
        "runtime_sha256": sha256(INSTALL / RUNTIME),
        "client_launcher": CLIENT_LAUNCHER.as_posix(),
        "server_launchers": server_launchers,
        "server_jars": server_jars,
        "backup_template": str(backup),
        "rollback_template": str(rollback),
        "active_xmage_modified": False,
        "backup_executed": False,
        "rollback_armed": False,
        "candidate_activated": False,
        "activation_allowed": False,
        "next_gate": "detect active XMage path + create verified full backup + arm rollback",
    }
    REPORT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    SUMMARY.write_text(
        "XMage Community Patch - CONTROLLED INSTALL PREP V1\n"
        "===================================================\n\n"
        "RESULT: PASS\n"
        "Status: CONTROLLED_INSTALL_READY_NOT_ACTIVATED\n"
        f"Candidate SHA-256: {actual}\n"
        f"Controlled installation: {INSTALL}\n"
        "Client: PASS\n"
        "Deck Downloader runtime: PASS\n"
        "Client launcher: PASS\n"
        f"Server launchers detected: {len(server_launchers)}\n"
        f"Server jars detected: {len(server_jars)}\n"
        "Backup template: PREPARED, NOT EXECUTED\n"
        "Rollback template: PREPARED, NOT ARMED\n\n"
        "Active XMage was NOT modified.\n"
        "Activation remains BLOCKED.\n"
        "Next gate must detect the real active XMage path and make a verified full backup first.\n",
        encoding="utf-8",
    )

    print("\n=== CONTROLLED INSTALL PREP V1 PASSED ===")
    print(f"Controlled copy: {INSTALL}")
    print(f"Manifest: {REPORT}")
    print(f"Summary: {SUMMARY}")
    print("Active XMage was NOT modified. Activation remains BLOCKED.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("CONTROLLED INSTALL PREP V1 FAILED SAFELY. Active XMage was NOT modified.")
        input("Press Enter to close...")
        raise SystemExit(1)
