#!/usr/bin/env python3
"""XMage Community Patch - SERVER MIGRATION PREFLIGHT V3.

SAFE MODE: does not replace the active server.
V3 removes the fragile PowerShell hard dependency from V2. It uses a practical
fail-safe model:
- optional WMIC process diagnostics when available;
- real H2 database copy probe as the authority for file locks;
- full rollback backup only after DB files are proven copyable;
- backup verified by SHA-256 tree comparison.

If the DB is locked, it stops before backup. If WMIC is missing/broken but the
DB copy probe passes, it continues because the lock that broke V1 is gone.
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
OUT = WORK / "preflight-v3"
REPORT = OUT / "SERVER_MIGRATION_PREFLIGHT_V3.json"
SUMMARY = OUT / "RESUMEN_SERVER_MIGRATION_PREFLIGHT_V3.txt"
ACTIVE = Path(r"J:\MTG\xmage\mage-server")


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
    files = sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: str(p.relative_to(root)).lower())
    for p in files:
        rel = str(p.relative_to(root)).replace("\\", "/").encode("utf-8")
        file_hash = sha256(p)
        size = p.stat().st_size
        h.update(rel + b"\0" + file_hash.encode() + b"\0" + str(size).encode() + b"\n")
        count += 1
        total += size
    return h.hexdigest(), count, total


def wmic_server_process_hints(active: Path) -> list[str]:
    """Best-effort diagnostics only. WMIC may be unavailable on modern Windows."""
    hints: list[str] = []
    try:
        cp = subprocess.run(
            ["wmic", "process", "where", "name='java.exe' or name='javaw.exe'", "get", "ProcessId,CommandLine", "/format:list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        if cp.returncode != 0:
            hints.append("WMIC unavailable or returned error; continuing with DB lock probe")
            return hints
        active_s = str(active).lower()
        for block in cp.stdout.split("\n\n"):
            b = block.strip()
            if not b:
                continue
            bl = b.lower()
            if active_s in bl or "mage-server" in bl or "mageserver" in bl:
                hints.append(b.replace("\n", " | "))
        return hints
    except Exception as exc:
        return [f"WMIC diagnostic unavailable: {exc}"]


def probe_copyable_db_files(active: Path) -> tuple[list[str], int]:
    """Authority check: if H2 DB copies, the server is not holding the broken lock."""
    db = active / "db"
    if not db.is_dir():
        return [], 0
    probe_dir = WORK / "lock-probe-v3"
    if probe_dir.exists():
        shutil.rmtree(probe_dir, ignore_errors=True)
    probe_dir.mkdir(parents=True, exist_ok=True)
    locked: list[str] = []
    checked = 0
    try:
        patterns = ["*.db", "*.mv.db", "*.trace.db", "*.lock.db"]
        seen = []
        for pat in patterns:
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


def find_clean_server() -> tuple[Path, list[tuple[int, Path]]]:
    candidates: list[tuple[int, Path]] = []
    search_roots = []
    if (ROOT / "staging").is_dir():
        search_roots.append(ROOT / "staging")
    search_roots.append(ROOT)
    seen = set()
    for search_root in search_roots:
        for p in search_root.rglob("mage-server"):
            if not p.is_dir():
                continue
            key = str(p).lower()
            if key in seen:
                continue
            seen.add(key)
            score = 0
            s = key
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
    print("=== XMage Community Patch - SERVER MIGRATION PREFLIGHT V3 ===")
    print("SAFE MODE: active server will NOT be replaced.")
    print("V3 uses DB lock probing as the authority and avoids fragile PowerShell.\n")

    require(ACTIVE.is_dir(), f"Active server not found: {ACTIVE}")
    active_jars = sorted((ACTIVE / "lib").glob("mage-server*.jar")) if (ACTIVE / "lib").is_dir() else []
    require(active_jars, "Active server has no mage-server JAR")
    print(f"[OK] Active server found: {ACTIVE}")
    print(f"[INFO] Active server JAR: {active_jars[-1].name}")

    print("[STEP 0/3] Best-effort Java/XMage diagnostics...")
    hints = wmic_server_process_hints(ACTIVE)
    real_hints = [h for h in hints if "WMIC" not in h]
    if real_hints:
        print("[WARN] Java/XMage process hints still visible:")
        for h in real_hints:
            print("  " + h)
        print("[INFO] Continuing only if DB lock probe passes.")
    else:
        for h in hints:
            print("[INFO] " + h)

    print("[STEP 0/3] Probing H2 database copy locks...")
    locked, checked = probe_copyable_db_files(ACTIVE)
    if locked:
        print("[BLOCK] H2 database file(s) are still locked:")
        for line in locked:
            print("  " + line)
        raise RuntimeError("Server database is still locked. Kill the java.exe server process and run V3 again.")
    print(f"[OK] H2 DB lock probe passed ({checked} DB file(s) checked)")

    candidate, ranked = find_clean_server()
    cand_jars = sorted((candidate / "lib").glob("mage-server*.jar"))
    require(cand_jars, f"Candidate server has no mage-server JAR: {candidate}")
    require(candidate.resolve() != ACTIVE.resolve(), "Candidate unexpectedly equals active server")
    print(f"[OK] Clean 1.4.61 server candidate: {candidate}")
    print(f"[INFO] Candidate server JAR: {cand_jars[-1].name}")

    OUT.mkdir(parents=True, exist_ok=True)
    backups = WORK / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / f"mage-server-1.4.60V3-pre-1.4.61V1_V3_{time.strftime('%Y%m%d-%H%M%S')}"

    print("[STEP 1/3] Creating full rollback backup of active server...")
    shutil.copytree(ACTIVE, backup, copy_function=shutil.copy2)

    print("[STEP 2/3] Verifying full backup SHA-256 tree...")
    active_hash, active_count, active_bytes = tree_digest(ACTIVE)
    backup_hash, backup_count, backup_bytes = tree_digest(backup)
    require((active_hash, active_count, active_bytes) == (backup_hash, backup_count, backup_bytes), "Server backup SHA-256 tree verification failed")
    print(f"[OK] Verified server backup: {active_count} files, {active_bytes} bytes")
    print(f"[OK] Server backup tree SHA-256: {active_hash}")

    print("[STEP 3/3] Recording verified 1.4.61 server candidate hashes...")
    candidate_hashes = {p.name: sha256(p) for p in cand_jars}
    for name, digest in candidate_hashes.items():
        print(f"[OK] {name}: {digest}")

    report = {
        "schema": 3,
        "phase": "SERVER_MIGRATION_PREFLIGHT_V3",
        "status": "SERVER_1_4_61V1_READY_NOT_ACTIVATED",
        "active_server": str(ACTIVE),
        "active_server_jar": str(active_jars[-1]),
        "candidate_server": str(candidate),
        "candidate_server_jars": candidate_hashes,
        "verified_backup": str(backup),
        "backup_tree_sha256": active_hash,
        "backup_files": active_count,
        "backup_bytes": active_bytes,
        "wmic_process_hints": hints,
        "h2_lock_check": "PASS",
        "active_server_modified": False,
        "candidate_activated": False,
        "activation_allowed": True,
        "next_gate": "CONTROLLED_SERVER_ACTIVATION_V1",
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    SUMMARY.write_text(
        "XMage Community Patch - SERVER MIGRATION PREFLIGHT V3\n"
        "=====================================================\n\n"
        "RESULT: PASS\n"
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

    print("\n=== SERVER MIGRATION PREFLIGHT V3 PASSED ===")
    print("Active server was NOT modified.")
    print("Verified rollback backup is ready.")
    print(f"Manifest: {REPORT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("SERVER MIGRATION PREFLIGHT V3 STOPPED SAFELY. Active server was NOT modified.")
        input("Press Enter to close...")
        raise SystemExit(1)
