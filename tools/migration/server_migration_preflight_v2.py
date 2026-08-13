#!/usr/bin/env python3
"""XMage Community Patch - SERVER MIGRATION PREFLIGHT V2.

SAFE MODE: does not replace the active server.
V2 fixes V1 failing mid-backup when H2 database files are locked by a running
server. It now performs a fail-closed process/port preflight BEFORE any copy.

It then creates and verifies a full byte-for-byte rollback backup and locates
the clean 1.4.61V1 server candidate already present in migration-workspace.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE / "migration-workspace"
WORK = ROOT / "server-port-1.4.61V1"
OUT = WORK / "preflight-v2"
REPORT = OUT / "SERVER_MIGRATION_PREFLIGHT_V2.json"
SUMMARY = OUT / "RESUMEN_SERVER_MIGRATION_PREFLIGHT_V2.txt"
ACTIVE = Path(r"J:\MTG\xmage\mage-server")
SERVER_PORT = 17171


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_digest(root: Path) -> tuple[str, int, int]:
    h = hashlib.sha256()
    count = 0
    total = 0
    files = sorted((p for p in root.rglob("*") if p.is_file()),
                   key=lambda p: str(p.relative_to(root)).lower())
    for p in files:
        rel = str(p.relative_to(root)).replace("\\", "/").encode("utf-8")
        file_hash = sha256(p)
        size = p.stat().st_size
        h.update(rel + b"\0" + file_hash.encode() + b"\0" + str(size).encode() + b"\n")
        count += 1
        total += size
    return h.hexdigest(), count, total


def powershell_lines(script: str) -> list[str]:
    cp = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    require(cp.returncode == 0, "PowerShell process inspection failed: " + cp.stderr.strip())
    return [line.strip() for line in cp.stdout.splitlines() if line.strip()]


def detect_server_processes(active: Path) -> list[str]:
    """Find real Java/XMage server processes and anything listening on 17171."""
    active_s = str(active).replace("'", "''")
    script = rf'''
$ErrorActionPreference='Stop'
$seen=@{{}}
Get-CimInstance Win32_Process | Where-Object {{
  $_.CommandLine -and $_.Name -match '^(java|javaw|cmd)\.exe$' -and
  ($_.CommandLine -like '*{active_s}*' -or $_.CommandLine -match 'mage-server|MageServer')
}} | ForEach-Object {{
  $seen[$_.ProcessId]=$true
  "PID=$($_.ProcessId) NAME=$($_.Name) CMD=$($_.CommandLine)"
}}
try {{
  Get-NetTCPConnection -State Listen -LocalPort {SERVER_PORT} -ErrorAction Stop | ForEach-Object {{
    if (-not $seen.ContainsKey($_.OwningProcess)) {{
      $p=Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)"
      if ($p) {{ "PID=$($p.ProcessId) NAME=$($p.Name) PORT={SERVER_PORT} CMD=$($p.CommandLine)" }}
      else {{ "PID=$($_.OwningProcess) PORT={SERVER_PORT} (process details unavailable)" }}
    }}
  }}
}} catch {{ }}
'''
    return powershell_lines(script)


def probe_locked_h2_files(active: Path) -> list[str]:
    """Use a real copy probe because Windows sharing locks are what broke V1."""
    locked: list[str] = []
    db = active / "db"
    if not db.is_dir():
        return locked
    probe_dir = WORK / "lock-probe-v2"
    if probe_dir.exists():
        shutil.rmtree(probe_dir, ignore_errors=True)
    probe_dir.mkdir(parents=True, exist_ok=True)
    try:
        for src in sorted(db.glob("*.db")) + sorted(db.glob("*.mv.db")) + sorted(db.glob("*.trace.db")):
            if not src.is_file():
                continue
            dst = probe_dir / src.name
            try:
                shutil.copy2(src, dst)
            except OSError as exc:
                locked.append(f"{src}: {exc}")
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)
    return locked


def find_clean_server() -> tuple[Path, list[tuple[int, Path]]]:
    candidates: list[tuple[int, Path]] = []
    staging = ROOT / "staging"
    search_roots = [staging] if staging.is_dir() else [ROOT]
    for search_root in search_roots:
        for p in search_root.rglob("mage-server"):
            if not p.is_dir():
                continue
            s = str(p).lower()
            score = 0
            if "1.4.61" in s:
                score += 100
            if "clean" in s:
                score += 60
            if "staging" in s:
                score += 20
            if "1.4.60" in s:
                score -= 200
            if "backup" in s:
                score -= 200
            if (p / "lib").is_dir():
                score += 20
            if any((p / "lib").glob("mage-server*.jar")):
                score += 40
            if any((p / n).is_file() for n in ("startServer.bat", "startServer.cmd")):
                score += 20
            candidates.append((score, p))
    require(candidates, "No mage-server candidate found in migration-workspace")
    candidates.sort(key=lambda x: x[0], reverse=True)
    best = candidates[0]
    require(best[0] >= 100, f"No trustworthy clean 1.4.61 server candidate found. Best={best}")
    return best[1], candidates[:10]


def main() -> int:
    print("=== XMage Community Patch - SERVER MIGRATION PREFLIGHT V2 ===")
    print("SAFE MODE: active server will NOT be replaced.")
    print("V2 checks running processes and H2 locks BEFORE creating the backup.\n")

    require(ACTIVE.is_dir(), f"Active server not found: {ACTIVE}")
    active_jars = sorted((ACTIVE / "lib").glob("mage-server*.jar")) if (ACTIVE / "lib").is_dir() else []
    require(active_jars, "Active server has no mage-server JAR")
    print(f"[OK] Active server found: {ACTIVE}")
    print(f"[INFO] Active server JAR: {active_jars[-1].name}")

    print("[STEP 0/3] Checking that the old server is completely stopped...")
    processes = detect_server_processes(ACTIVE)
    if processes:
        print("[BLOCK] Server-related process/listener still detected:")
        for line in processes:
            print("  " + line)
        raise RuntimeError("Server is still running or port 17171 is still in use. Close/stop it and run V2 again.")

    locked = probe_locked_h2_files(ACTIVE)
    if locked:
        print("[BLOCK] H2 database file(s) are still locked:")
        for line in locked:
            print("  " + line)
        raise RuntimeError("Server database is still locked. Close the process holding it and run V2 again.")
    print("[OK] No server process, listener, or H2 database lock detected")

    candidate, ranked = find_clean_server()
    cand_jars = sorted((candidate / "lib").glob("mage-server*.jar"))
    require(cand_jars, f"Candidate server has no mage-server JAR: {candidate}")
    require(candidate.resolve() != ACTIVE.resolve(), "Candidate unexpectedly equals active server")
    print(f"[OK] Clean 1.4.61 server candidate: {candidate}")
    print(f"[INFO] Candidate server JAR: {cand_jars[-1].name}")

    OUT.mkdir(parents=True, exist_ok=True)
    backups = WORK / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / f"mage-server-1.4.60V3-pre-1.4.61V1_V2_{time.strftime('%Y%m%d-%H%M%S')}"

    print("[STEP 1/3] Creating full rollback backup of active server...")
    try:
        shutil.copytree(ACTIVE, backup, copy_function=shutil.copy2)
    except Exception:
        # Partial backup is deliberately kept for forensic purposes; it is never accepted as verified.
        raise

    print("[STEP 2/3] Verifying full backup SHA-256 tree...")
    active_hash, active_count, active_bytes = tree_digest(ACTIVE)
    backup_hash, backup_count, backup_bytes = tree_digest(backup)
    require(
        (active_hash, active_count, active_bytes) == (backup_hash, backup_count, backup_bytes),
        "Server backup SHA-256 tree verification failed",
    )
    print(f"[OK] Verified server backup: {active_count} files, {active_bytes} bytes")
    print(f"[OK] Server backup tree SHA-256: {active_hash}")

    print("[STEP 3/3] Recording verified 1.4.61 server candidate hashes...")
    candidate_hashes = {p.name: sha256(p) for p in cand_jars}
    for name, digest in candidate_hashes.items():
        print(f"[OK] {name}: {digest}")

    report = {
        "schema": 2,
        "phase": "SERVER_MIGRATION_PREFLIGHT_V2",
        "status": "SERVER_1_4_61V1_READY_NOT_ACTIVATED",
        "active_server": str(ACTIVE),
        "active_server_jar": str(active_jars[-1]),
        "candidate_server": str(candidate),
        "candidate_server_jars": candidate_hashes,
        "verified_backup": str(backup),
        "backup_tree_sha256": active_hash,
        "backup_files": active_count,
        "backup_bytes": active_bytes,
        "process_lock_check": "PASS",
        "h2_lock_check": "PASS",
        "active_server_modified": False,
        "candidate_activated": False,
        "activation_allowed": True,
        "next_gate": "CONTROLLED_SERVER_ACTIVATION_V1",
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    SUMMARY.write_text(
        "XMage Community Patch - SERVER MIGRATION PREFLIGHT V2\n"
        "=====================================================\n\n"
        "RESULT: PASS\n"
        "Process/listener lock check: PASS\n"
        "H2 database lock check: PASS\n"
        f"Active server: {ACTIVE}\n"
        f"Candidate server: {candidate}\n"
        f"Verified backup: {backup}\n"
        f"Backup tree SHA-256: {active_hash}\n"
        "Active server modified: NO\n"
        "Candidate activated: NO\n"
        "Next gate: CONTROLLED_SERVER_ACTIVATION_V1\n",
        encoding="utf-8",
    )

    print("\n=== SERVER MIGRATION PREFLIGHT V2 PASSED ===")
    print("Active server was NOT modified.")
    print("Verified rollback backup is ready.")
    print(f"Manifest: {REPORT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("SERVER MIGRATION PREFLIGHT V2 STOPPED SAFELY. Active server was NOT modified.")
        input("Press Enter to close...")
        raise SystemExit(1)
