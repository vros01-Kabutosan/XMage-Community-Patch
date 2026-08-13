#!/usr/bin/env python3
"""XMage Community Patch - CONTROLLED ACTIVATION PREFLIGHT V1.

SAFE MODE: this gate does NOT modify or activate the active XMage installation.

It cross-checks the previously verified controlled-install candidate and the
verified BACKUP + ROLLBACK GATE V4 manifest, re-verifies critical hashes, checks
that the active XMage path is still the expected one, confirms the backup still
exists, and writes an ARMED rollback script that is safe to execute only after a
future controlled activation step.

Output state: READY_FOR_CONTROLLED_ACTIVATION, but no files are replaced here.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "migration-workspace" / "port-1.4.61V1"
CONTROL = WORK / "controlled-install-v1"
CONTROL_MANIFEST = CONTROL / "CONTROLLED_INSTALL_PREP_V1.json"
BACKUP_GATE_DIR = WORK / "backup-rollback-gate-v4"
BACKUP_MANIFEST = BACKUP_GATE_DIR / "BACKUP_ROLLBACK_GATE_V4.json"
OUT = WORK / "controlled-activation-preflight-v1"
REPORT = OUT / "CONTROLLED_ACTIVATION_PREFLIGHT_V1.json"
SUMMARY = OUT / "RESUMEN_CONTROLLED_ACTIVATION_PREFLIGHT_V1.txt"
ROLLBACK = OUT / "ROLLBACK_ACTIVE_XMAGE_ARMED_V1.cmd"

EXPECTED_ACTIVE = Path(r"J:\MTG\xmage\mage-client")


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


def same_path(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return str(a).lower() == str(b).lower()


def write_armed_rollback(active: Path, backup: Path) -> None:
    """Prepare a real rollback script, but do not execute it in this gate."""
    temp_restore = active.parent / (active.name + ".ROLLBACK_RESTORE_V1")
    old_failed = active.parent / (active.name + ".FAILED_ACTIVATION_V1")

    content = rf'''@echo off
setlocal EnableExtensions
title XMage Community Patch - ARMED ROLLBACK V1

echo ============================================================
echo XMage Community Patch - ARMED ROLLBACK V1
echo ============================================================
echo.
echo This will RESTORE the verified pre-activation backup.
echo Active: {active}
echo Backup: {backup}
echo.
if not exist "{backup}\" (
  echo ERROR: Verified backup folder is missing.
  pause
  exit /b 2
)
if not exist "{backup}\lib\" (
  echo ERROR: Backup does not look like an XMage client installation.
  pause
  exit /b 3
)

echo IMPORTANT: close XMage client/server/launcher before continuing.
choice /C YN /N /M "Restore verified backup now? [Y/N] "
if errorlevel 2 exit /b 1

if exist "{temp_restore}\" rmdir /S /Q "{temp_restore}"
echo [1/4] Copying verified backup to temporary restore folder...
robocopy "{backup}" "{temp_restore}" /MIR /COPY:DAT /DCOPY:DAT /R:2 /W:2 /NFL /NDL /NP
set RC=%errorlevel%
if %RC% GEQ 8 (
  echo ERROR: Backup copy failed with robocopy code %RC%.
  pause
  exit /b %RC%
)

echo [2/4] Preserving current failed installation...
if exist "{old_failed}\" rmdir /S /Q "{old_failed}"
if exist "{active}\" move "{active}" "{old_failed}" >nul
if errorlevel 1 (
  echo ERROR: Could not move current active installation. Is XMage still open?
  pause
  exit /b 10
)

echo [3/4] Restoring backup into active path...
move "{temp_restore}" "{active}" >nul
if errorlevel 1 (
  echo CRITICAL: Could not move restored backup into active path.
  echo Attempting emergency recovery of previous installation...
  if exist "{old_failed}\" move "{old_failed}" "{active}" >nul
  pause
  exit /b 11
)

echo [4/4] Rollback completed.
echo Previous failed installation kept at:
echo {old_failed}
echo.
echo Start XMage normally and verify it works before deleting that folder.
pause
exit /b 0
'''
    ROLLBACK.write_text(content, encoding="utf-8")


def main() -> int:
    print("=== XMage Community Patch - CONTROLLED ACTIVATION PREFLIGHT V1 ===")
    print("SAFE MODE: no active XMage files will be modified.\n")

    control = load_json(CONTROL_MANIFEST)
    backup_gate = load_json(BACKUP_MANIFEST)

    require(control.get("status") == "CONTROLLED_INSTALL_READY_NOT_ACTIVATED",
            "Controlled Install Prep V1 is not in READY_NOT_ACTIVATED state")
    require(control.get("active_xmage_modified") is False,
            "Controlled Install Prep V1 does not prove active XMage remained untouched")
    require(control.get("candidate_activated") is False,
            "Controlled Install Prep V1 unexpectedly reports candidate already activated")

    require(backup_gate.get("status") == "VERIFIED_BACKUP_READY_ACTIVATION_STILL_BLOCKED",
            "Backup + Rollback Gate V4 is not in verified backup state")
    require(backup_gate.get("backup_verified") is True,
            "Backup + Rollback Gate V4 does not report a verified backup")
    require(backup_gate.get("candidate_activated") is False,
            "Backup + Rollback Gate V4 unexpectedly reports candidate already activated")
    require(backup_gate.get("active_xmage_modified_by_gate") is False,
            "Backup + Rollback Gate V4 modified active XMage unexpectedly")

    print("[OK] Prior safety manifests are consistent")

    active = Path(str(backup_gate.get("active_xmage", "")))
    backup = Path(str(backup_gate.get("backup", "")))
    install = Path(str(control.get("installation_root", "")))

    require(active.is_dir(), f"Active XMage path missing: {active}")
    require(same_path(active, EXPECTED_ACTIVE),
            f"Active XMage path changed. Expected {EXPECTED_ACTIVE}, got {active}")
    require(backup.is_dir(), f"Verified backup folder missing: {backup}")
    require(install.is_dir(), f"Controlled candidate installation missing: {install}")
    print(f"[OK] Active XMage path still fixed: {active}")
    print(f"[OK] Verified backup still present: {backup}")
    print(f"[OK] Controlled candidate still present: {install}")

    client_rel = Path(str(control.get("client", "")))
    runtime_rel = Path(str(control.get("runtime", "")))
    launcher_rel = Path(str(control.get("client_launcher", "")))
    candidate_client = install / client_rel
    candidate_runtime = install / runtime_rel
    candidate_launcher = install / launcher_rel

    require(candidate_client.is_file(), f"Candidate client missing: {candidate_client}")
    require(candidate_runtime.is_file(), f"Candidate runtime missing: {candidate_runtime}")
    require(candidate_launcher.is_file(), f"Candidate launcher missing: {candidate_launcher}")

    expected_client_hash = control.get("client_sha256")
    expected_runtime_hash = control.get("runtime_sha256")
    actual_client_hash = sha256(candidate_client)
    actual_runtime_hash = sha256(candidate_runtime)
    require(actual_client_hash == expected_client_hash,
            "Candidate mage-client JAR changed since Controlled Install Prep V1")
    require(actual_runtime_hash == expected_runtime_hash,
            "Deck Downloader runtime changed since Controlled Install Prep V1")
    print("[OK] Candidate client SHA-256 unchanged")
    print("[OK] Deck Downloader runtime SHA-256 unchanged")

    backup_client = backup / "lib" / next(iter([p.name for p in (backup / "lib").glob("mage-client*.jar")]), "")
    require((backup / "lib").is_dir(), "Verified backup is missing lib directory")
    require(any((backup / "lib").glob("mage-client*.jar")),
            "Verified backup is missing mage-client JAR")
    require(any((active / "lib").glob("mage-client*.jar")),
            "Active XMage is missing mage-client JAR")
    print("[OK] Active and backup both still look like XMage client installations")

    # Quick backup integrity spot-check: verify the backup client JAR equals its matching active JAR
    backup_jars = sorted((backup / "lib").glob("mage-client*.jar"))
    active_jars = sorted((active / "lib").glob("mage-client*.jar"))
    common = {p.name: p for p in active_jars}
    matched = [(bp, common[bp.name]) for bp in backup_jars if bp.name in common]
    require(matched, "No matching mage-client JAR name between active XMage and verified backup")
    for bp, ap in matched:
        require(sha256(bp) == sha256(ap),
                f"Active XMage changed since backup verification: {ap.name}")
    print(f"[OK] Active critical client JAR still matches verified backup ({len(matched)} match)")

    OUT.mkdir(parents=True, exist_ok=True)
    write_armed_rollback(active, backup)
    require(ROLLBACK.is_file(), "Failed to write armed rollback script")
    print(f"[OK] Armed rollback script prepared: {ROLLBACK}")

    report = {
        "schema": 1,
        "phase": "CONTROLLED_ACTIVATION_PREFLIGHT_V1",
        "status": "READY_FOR_CONTROLLED_ACTIVATION",
        "active_xmage": str(active),
        "expected_active_xmage": str(EXPECTED_ACTIVE),
        "backup": str(backup),
        "backup_verified_by_v4": True,
        "controlled_candidate": str(install),
        "candidate_client_sha256": actual_client_hash,
        "candidate_runtime_sha256": actual_runtime_hash,
        "rollback_script": str(ROLLBACK),
        "rollback_armed": True,
        "active_xmage_modified_by_gate": False,
        "candidate_activated": False,
        "activation_allowed": True,
        "next_gate": "CONTROLLED_ACTIVATION_V1",
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    SUMMARY.write_text(
        "XMage Community Patch - CONTROLLED ACTIVATION PREFLIGHT V1\n"
        "===========================================================\n\n"
        "RESULT: PASS\n"
        "Status: READY_FOR_CONTROLLED_ACTIVATION\n"
        f"Active XMage: {active}\n"
        f"Verified backup: {backup}\n"
        f"Controlled candidate: {install}\n"
        "Candidate client hash: PASS\n"
        "Deck Downloader runtime hash: PASS\n"
        "Active critical client vs backup: PASS\n"
        "Rollback: ARMED\n"
        "Active XMage modified by this gate: NO\n"
        "Candidate activated: NO\n"
        "Next gate: CONTROLLED_ACTIVATION_V1\n",
        encoding="utf-8",
    )

    print("\n=== CONTROLLED ACTIVATION PREFLIGHT V1 PASSED ===")
    print(f"Manifest: {REPORT}")
    print(f"Summary: {SUMMARY}")
    print(f"Rollback armed: {ROLLBACK}")
    print("No active XMage files were modified. Controlled activation is now permitted for the NEXT gate only.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("CONTROLLED ACTIVATION PREFLIGHT V1 STOPPED SAFELY. Active XMage was NOT modified.")
        input("Press Enter to close...")
        raise SystemExit(1)
