#!/usr/bin/env python3
"""XMage Community Patch - CONTROLLED SERVER ACTIVATION V1.

Replaces the active local XMage server with the verified clean 1.4.61V1 server
candidate prepared by SERVER_MIGRATION_PREFLIGHT_V3.

Safety properties:
- requires preflight V3 PASS manifest;
- verifies candidate JAR SHA-256 before and after staging;
- checks H2 DB files are not locked before activation;
- preserves the current active server as immediate rollback folder;
- preserves the verified preflight backup;
- writes an explicit rollback script;
- does not touch mage-client, images, decks, launcher or installed.properties.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "migration-workspace" / "server-port-1.4.61V1"
PREFLIGHT = WORK / "preflight-v3" / "SERVER_MIGRATION_PREFLIGHT_V3.json"
OUT = WORK / "controlled-server-activation-v1"
REPORT = OUT / "CONTROLLED_SERVER_ACTIVATION_V1.json"
SUMMARY = OUT / "RESUMEN_CONTROLLED_SERVER_ACTIVATION_V1.txt"
EXPECTED_ACTIVE = Path(r"J:\MTG\xmage\mage-server")

SAFE_PRESERVE_EXTENSIONS = {".properties", ".xml", ".json", ".txt", ".cfg", ".conf", ".ini"}
NEVER_PRESERVE_DIRS = {"db", "lib", "target", "build", "__pycache__", ".git", ".github"}
NEVER_PRESERVE_EXTENSIONS = {".jar", ".class", ".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".ps1", ".sh", ".py", ".pyc", ".pyo", ".db"}


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    require(path.is_file(), f"Missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def same_path(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return str(a).lower() == str(b).lower()


def tree_digest(root: Path) -> tuple[str, int, int]:
    h = hashlib.sha256()
    count = 0
    total = 0
    files = sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: str(p.relative_to(root)).lower())
    for p in files:
        rel = str(p.relative_to(root)).replace("\\", "/").encode("utf-8")
        digest = sha256(p)
        size = p.stat().st_size
        h.update(rel + b"\0" + digest.encode() + b"\0" + str(size).encode() + b"\n")
        count += 1
        total += size
    return h.hexdigest(), count, total


def probe_copyable_db_files(active: Path) -> tuple[list[str], int]:
    db = active / "db"
    if not db.is_dir():
        return [], 0
    probe_dir = WORK / "activation-lock-probe-v1"
    if probe_dir.exists():
        shutil.rmtree(probe_dir, ignore_errors=True)
    probe_dir.mkdir(parents=True, exist_ok=True)
    locked: list[str] = []
    checked = 0
    try:
        seen: list[Path] = []
        for pat in ("*.db", "*.mv.db", "*.trace.db", "*.lock.db"):
            for src in db.glob(pat):
                if src.is_file() and src not in seen:
                    seen.append(src)
        for src in sorted(seen):
            checked += 1
            try:
                shutil.copy2(src, probe_dir / src.name)
            except OSError as exc:
                locked.append(f"{src}: {exc}")
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)
    return locked, checked


def copytree(src: Path, dst: Path) -> tuple[int, int]:
    count = 0
    total = 0
    for root, dirs, files in os.walk(src):
        sr = Path(root)
        dr = dst / sr.relative_to(src)
        dr.mkdir(parents=True, exist_ok=True)
        for name in files:
            s = sr / name
            d = dr / name
            shutil.copy2(s, d)
            count += 1
            total += s.stat().st_size
    return count, total


def preserve_safe_missing_server_config(active: Path, stage: Path) -> tuple[int, int]:
    """Copy only harmless missing text config files. Candidate files always win."""
    copied = 0
    skipped = 0
    for root, dirs, files in os.walk(active):
        sr = Path(root)
        rel_dir = sr.relative_to(active)
        parts_lower = {p.lower() for p in rel_dir.parts}
        dirs[:] = [d for d in dirs if d.lower() not in NEVER_PRESERVE_DIRS]
        if parts_lower & NEVER_PRESERVE_DIRS:
            continue
        for name in files:
            s = sr / name
            rel = rel_dir / name
            ext = s.suffix.lower()
            if ext in NEVER_PRESERVE_EXTENSIONS or ext not in SAFE_PRESERVE_EXTENSIONS:
                skipped += 1
                continue
            d = stage / rel
            if d.exists():
                skipped += 1
                continue
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
            copied += 1
    return copied, skipped


def verify_server_candidate(server: Path, expected_hashes: dict[str, str]) -> dict[str, str]:
    require(server.is_dir(), f"Server folder missing: {server}")
    jars = sorted((server / "lib").glob("mage-server*.jar")) if (server / "lib").is_dir() else []
    require(jars, f"No mage-server JAR found in: {server}")
    found = {p.name: sha256(p) for p in jars}
    for name, digest in expected_hashes.items():
        require(name in found, f"Expected server JAR missing from candidate: {name}")
        require(found[name] == digest, f"Server JAR SHA-256 mismatch for {name}")
    return found


def write_rollback_script(path: Path, active: Path, previous: Path, verified_backup: Path) -> None:
    content = f'''@echo off
setlocal
set "ACTIVE={active}"
set "PREVIOUS={previous}"
set "VERIFIED_BACKUP={verified_backup}"
echo ================================================================
echo XMage Community Patch - ROLLBACK ACTIVE SERVER V1
echo ================================================================
echo.
echo This restores the pre-activation mage-server folder.
echo Active: %ACTIVE%
echo Previous: %PREVIOUS%
echo Verified backup: %VERIFIED_BACKUP%
echo.
set /p CONFIRM=Run server rollback now? [Y/N] 
if /I not "%CONFIRM%"=="Y" exit /b 1
if not exist "%PREVIOUS%" (
  echo ERROR: Previous server folder missing.
  echo You still have the verified backup at: %VERIFIED_BACKUP%
  pause
  exit /b 1
)
if exist "%ACTIVE%" ren "%ACTIVE%" "mage-server.FAILED_AFTER_SERVER_ACTIVATION_V1_%DATE:/=-%_%TIME::=-%"
ren "%PREVIOUS%" "mage-server"
echo Rollback completed. Previous server restored as active mage-server.
pause
'''
    path.write_text(content, encoding="utf-8")


def main() -> int:
    print("=== XMage Community Patch - CONTROLLED SERVER ACTIVATION V1 ===")
    print("WARNING: this gate CAN replace the active local mage-server.")
    print("It does NOT touch mage-client, images, decks, launcher or installed.properties.\n")

    confirm = input("Run CONTROLLED SERVER ACTIVATION V1 now? [Y/N]: ").strip().lower()
    if confirm not in ("y", "yes", "s", "si", "sí"):
        print("Cancelled by user. Nothing was modified.")
        return 1

    pf = load_json(PREFLIGHT)
    require(pf.get("status") == "SERVER_1_4_61V1_READY_NOT_ACTIVATED", "Server preflight V3 is not ready")
    require(pf.get("activation_allowed") is True, "Preflight does not allow activation")
    require(pf.get("active_server_modified") is False, "Preflight state is not clean")
    require(pf.get("candidate_activated") is False, "Candidate was already activated according to preflight")
    active = Path(str(pf.get("active_server", "")))
    candidate = Path(str(pf.get("candidate_server", "")))
    verified_backup = Path(str(pf.get("verified_backup", "")))
    expected_hashes = dict(pf.get("candidate_server_jars", {}))

    require(active.is_dir(), f"Active server missing: {active}")
    require(same_path(active, EXPECTED_ACTIVE), f"Unexpected active server path: {active}")
    require(candidate.is_dir(), f"Candidate server missing: {candidate}")
    require(verified_backup.is_dir(), f"Verified backup missing: {verified_backup}")
    require(expected_hashes, "Candidate server hashes missing from preflight")
    print("[OK] Preflight V3 manifest verified")
    print(f"[OK] Active server: {active}")
    print(f"[OK] Candidate server: {candidate}")
    print(f"[OK] Verified backup: {verified_backup}")

    locked, checked = probe_copyable_db_files(active)
    if locked:
        print("[BLOCK] Active server DB is locked:")
        for line in locked:
            print("  " + line)
        raise RuntimeError("Server appears to be running. Close/kill it and retry.")
    print(f"[OK] Active server DB lock probe passed ({checked} DB file(s) checked)")

    print("[STEP 1/6] Verifying candidate server hashes...")
    candidate_hashes = verify_server_candidate(candidate, expected_hashes)
    print("[OK] Candidate hashes match preflight")

    OUT.mkdir(parents=True, exist_ok=True)
    parent = active.parent
    stamp = time.strftime("%Y%m%d-%H%M%S")
    stage = parent / f"mage-server.ACTIVATION_STAGE_V1_{stamp}"
    previous = parent / f"mage-server.PRE_SERVER_ACTIVATION_V1_{stamp}"
    rollback_script = OUT / "ROLLBACK_ACTIVE_SERVER_V1.cmd"

    if stage.exists():
        shutil.rmtree(stage)

    print("[STEP 2/6] Building staged 1.4.61 server...")
    files, bytes_total = copytree(candidate, stage)
    print(f"[OK] Candidate copied to stage: {files} files, {bytes_total} bytes")

    print("[STEP 3/6] Preserving harmless missing server text config only...")
    preserved, skipped = preserve_safe_missing_server_config(active, stage)
    print(f"[OK] Preserved missing config files={preserved}; skipped={skipped}")

    print("[STEP 4/6] Verifying staged server hashes...")
    staged_hashes = verify_server_candidate(stage, expected_hashes)
    print("[OK] Staged server hashes verified")

    print("[STEP 5/6] Writing rollback script...")
    write_rollback_script(rollback_script, active, previous, verified_backup)
    print(f"[OK] Rollback script armed: {rollback_script}")

    pending = {
        "schema": 1,
        "phase": "CONTROLLED_SERVER_ACTIVATION_V1",
        "status": "SERVER_ACTIVATION_SWAP_PENDING",
        "active_server": str(active),
        "candidate_server": str(candidate),
        "stage": str(stage),
        "previous_server": str(previous),
        "verified_backup": str(verified_backup),
        "rollback_script": str(rollback_script),
        "candidate_server_jars": candidate_hashes,
        "staged_server_jars": staged_hashes,
        "active_server_modified": False,
    }
    REPORT.write_text(json.dumps(pending, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[STEP 6/6] Atomic server activation swap...")
    try:
        active.rename(previous)
    except OSError as exc:
        raise RuntimeError(f"Could not preserve current active server: {exc}")
    try:
        stage.rename(active)
    except OSError as exc:
        try:
            previous.rename(active)
        except OSError as restore_exc:
            raise RuntimeError(f"CRITICAL: swap failed and restore failed. Previous at {previous}. swap={exc}; restore={restore_exc}")
        raise RuntimeError(f"Swap failed; original server restored automatically: {exc}")

    print("[POST] Verifying active server after swap...")
    active_hashes_after = verify_server_candidate(active, expected_hashes)
    active_tree, active_count, active_bytes = tree_digest(active)

    result = {
        **pending,
        "status": "CONTROLLED_SERVER_ACTIVATION_COMPLETED_POST_SMOKE_REQUIRED",
        "active_server_modified": True,
        "candidate_activated": True,
        "active_server_jars_after": active_hashes_after,
        "active_server_tree_sha256_after": active_tree,
        "active_server_files_after": active_count,
        "active_server_bytes_after": active_bytes,
        "post_server_smoke_passed": False,
        "cleanup_allowed": False,
        "next_gate": "SERVER_POST_ACTIVATION_SMOKE_V1",
    }
    REPORT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    SUMMARY.write_text(
        "XMage Community Patch - CONTROLLED SERVER ACTIVATION V1\n"
        "========================================================\n\n"
        "RESULT: PASS\n"
        "Status: CONTROLLED_SERVER_ACTIVATION_COMPLETED_POST_SMOKE_REQUIRED\n"
        f"Active server: {active}\n"
        f"Previous server preserved: {previous}\n"
        f"Verified preflight backup preserved: {verified_backup}\n"
        f"Rollback script: {rollback_script}\n"
        "Server activated: YES\n"
        "Post-server smoke required: YES\n"
        "Cleanup allowed: NO\n"
        "Next gate: SERVER_POST_ACTIVATION_SMOKE_V1\n",
        encoding="utf-8",
    )

    print("\n=== CONTROLLED SERVER ACTIVATION V1 COMPLETED ===")
    print(f"Active server is now: {active}")
    print(f"Previous server preserved: {previous}")
    print(f"Verified preflight backup preserved: {verified_backup}")
    print(f"Rollback script: {rollback_script}")
    print("Next: SERVER_POST_ACTIVATION_SMOKE_V1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("CONTROLLED SERVER ACTIVATION V1 STOPPED/ROLLED BACK SAFELY WHERE POSSIBLE.")
        input("Press Enter to close...")
        raise SystemExit(1)
