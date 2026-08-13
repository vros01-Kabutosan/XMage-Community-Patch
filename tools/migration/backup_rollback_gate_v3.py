#!/usr/bin/env python3
"""XMage Community Patch - BACKUP + ROLLBACK GATE V3.

SAFE MODE:
- never activates the 1.4.61V1 candidate;
- never overwrites active XMage;
- reads processes/filesystem to discover the real active XMage;
- creates a verified backup only after one unambiguous installation is resolved.

V3 fixes V1/V2 assumptions by using multiple discovery methods:
1) running process command lines (java/javaw/cmd/powershell) mentioning XMage/mage-client;
2) recursive discovery of mage-client*.jar and startClient* launchers;
3) XMageLauncher*.jar and installed.properties hints;
4) root reconstruction from nested lib/mage-client*.jar layouts.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "migration-workspace" / "port-1.4.61V1"
CONTROL = WORK / "controlled-install-v1"
PREP = CONTROL / "CONTROLLED_INSTALL_PREP_V1.json"
OUT = WORK / "backup-rollback-gate-v3"
BACKUPS = OUT / "backups"
REPORT = OUT / "BACKUP_ROLLBACK_GATE_V3.json"
SUMMARY = OUT / "RESUMEN_BACKUP_ROLLBACK_GATE_V3.txt"

LAUNCHERS = ("startClient.bat", "startClientWin7.bat", "startClient.cmd", "startClientWin7.cmd")
SKIP_NAMES = {
    "$recycle.bin", "system volume information", "windows", "program files",
    "program files (x86)", "programdata", ".git", "node_modules", "migration-workspace"
}
EXCLUDE_FRAGMENTS = ("migration-workspace", "controlled-install-v1", "xmage-community-patch-hardening-update-architecture")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def normalize_root_from_path(path: Path) -> Path | None:
    """Infer an XMage installation root from a file/dir anywhere inside it."""
    try:
        p = path.resolve()
    except OSError:
        p = path
    if p.is_file():
        # mage-client*.jar normally lives in <root>/lib/
        if p.name.lower().startswith("mage-client") and p.parent.name.lower() == "lib":
            return p.parent.parent
        p = p.parent

    # exact root first
    if is_xmage_root(p):
        return p

    # walk upward several levels looking for a coherent XMage root
    cur = p
    for _ in range(7):
        if is_xmage_root(cur):
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def is_excluded(path: Path) -> bool:
    s = str(path).lower()
    return any(fragment in s for fragment in EXCLUDE_FRAGMENTS)


def is_xmage_root(root: Path) -> bool:
    if is_excluded(root) or not root.is_dir():
        return False
    lib = root / "lib"
    client_jars = list(lib.glob("mage-client*.jar")) if lib.is_dir() else []
    launchers = [root / n for n in LAUNCHERS if (root / n).is_file()]
    # Strong root: launcher + client jar.
    if client_jars and launchers:
        return True
    # Some launcher-managed layouts can lack a root BAT but still have config + lib client.
    if client_jars and ((root / "config").is_dir() or (root / "xmage").is_dir()):
        return True
    return False


def powershell_process_hints() -> list[Path]:
    """Read-only process inspection; extracts absolute Windows paths from command lines."""
    hints: list[Path] = []
    script = (
        "$ErrorActionPreference='SilentlyContinue'; "
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.CommandLine -match '(?i)(xmage|mage-client|XMageLauncher)' } | "
        "ForEach-Object { $_.CommandLine }"
    )
    try:
        cp = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            encoding="utf-8", errors="replace", timeout=30,
        )
    except Exception:
        return hints

    # Extract quoted and unquoted absolute paths ending in useful artifacts.
    patterns = [
        r'([A-Za-z]:\\[^"\r\n]*?mage-client[^"\r\n]*?\.jar)',
        r'([A-Za-z]:\\[^"\r\n]*?XMageLauncher[^"\r\n]*?\.jar)',
        r'([A-Za-z]:\\[^"\r\n]*?startClient(?:Win7)?\.(?:bat|cmd))',
    ]
    for line in cp.stdout.splitlines():
        for pat in patterns:
            for m in re.finditer(pat, line, re.I):
                hints.append(Path(m.group(1).strip(' "')))
    return hints


def plausible_bases() -> list[Path]:
    bases: list[Path] = []
    for key in ("USERPROFILE", "LOCALAPPDATA", "APPDATA"):
        val = os.environ.get(key)
        if val:
            bases.append(Path(val))
    # Search all mounted Windows drives, but system dirs are aggressively pruned.
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = Path(f"{letter}:/")
        if drive.exists():
            bases.append(drive)
    # dedupe
    out=[]; seen=set()
    for b in bases:
        try: r=b.resolve()
        except OSError: r=b
        k=str(r).lower()
        if k not in seen:
            seen.add(k); out.append(r)
    return out


def filesystem_hints(max_depth: int = 8) -> list[Path]:
    hints: list[Path] = []
    targets_exact = {n.lower() for n in LAUNCHERS} | {"installed.properties"}
    for base in plausible_bases():
        try:
            base_parts = len(base.parts)
        except Exception:
            base_parts = 0
        for root_s, dirs, files in os.walk(base, topdown=True):
            root = Path(root_s)
            try:
                depth = len(root.parts) - base_parts
            except Exception:
                depth = 0
            if depth >= max_depth:
                dirs[:] = []
            dirs[:] = [
                d for d in dirs
                if d.lower() not in SKIP_NAMES and not d.startswith("$")
                and "migration-workspace" not in str(root / d).lower()
            ]
            lowfiles = {f.lower(): f for f in files}
            for low, original in lowfiles.items():
                if low.startswith("mage-client") and low.endswith(".jar"):
                    hints.append(root / original)
                elif low.startswith("xmagelauncher") and low.endswith(".jar"):
                    hints.append(root / original)
                elif low in targets_exact:
                    hints.append(root / original)
    return hints


def roots_from_hints(hints: list[Path]) -> dict[Path, dict]:
    candidates: dict[Path, dict] = {}
    for hint in hints:
        root = normalize_root_from_path(hint)
        if root is None or is_excluded(root):
            continue
        entry = candidates.setdefault(root, {"hints": [], "score": 0})
        hs = str(hint)
        if hs not in entry["hints"]:
            entry["hints"].append(hs)
        name = hint.name.lower()
        if name.startswith("mage-client") and name.endswith(".jar"):
            entry["score"] += 10
        elif name.startswith("startclient"):
            entry["score"] += 8
        elif name.startswith("xmagelauncher"):
            entry["score"] += 4
        elif name == "installed.properties":
            entry["score"] += 2
    # bonus for coherent structure
    for root, entry in candidates.items():
        if (root / "lib").is_dir() and any((root / "lib").glob("mage-client*.jar")):
            entry["score"] += 20
        if any((root / n).is_file() for n in LAUNCHERS):
            entry["score"] += 15
        if (root / "config").is_dir():
            entry["score"] += 5
    return candidates


def resolve_single_candidate(candidates: dict[Path, dict]) -> tuple[Path, dict]:
    require(candidates, "No active XMage installation could be discovered. Gate stopped safely.")
    ranked = sorted(candidates.items(), key=lambda x: x[1]["score"], reverse=True)
    print(f"[INFO] XMage installation candidates found: {len(ranked)}")
    for i, (root, meta) in enumerate(ranked, 1):
        print(f"  {i}. score={meta['score']}  {root}")

    if len(ranked) == 1:
        return ranked[0]

    top_root, top_meta = ranked[0]
    second_score = ranked[1][1]["score"]
    # Only auto-select if substantially stronger than every alternative.
    require(
        top_meta["score"] >= 35 and top_meta["score"] >= second_score + 15,
        "Multiple plausible XMage installations found and none is unambiguous. Nothing was modified.",
    )
    print("[OK] Highest-scoring installation is unambiguous by evidence margin")
    return top_root, top_meta


def tree_digest(root: Path) -> tuple[str, int, int]:
    h = hashlib.sha256(); count = 0; total = 0
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        rel = p.relative_to(root).as_posix().encode("utf-8", "surrogatepass")
        size = p.stat().st_size
        h.update(rel); h.update(b"\0")
        h.update(str(size).encode()); h.update(b"\0")
        h.update(sha256(p).encode()); h.update(b"\n")
        count += 1; total += size
    return h.hexdigest(), count, total


def main() -> int:
    print("=== XMage Community Patch - BACKUP + ROLLBACK GATE V3 ===")
    print("SAFE MODE: candidate activation remains BLOCKED. Detection is read-only.\n")

    require(PREP.is_file(), f"Missing controlled-install manifest: {PREP}")
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    require(prep.get("status") == "CONTROLLED_INSTALL_READY_NOT_ACTIVATED", "Controlled Install Prep V1 is not ready")
    require(prep.get("active_xmage_modified") is False, "Previous gate does not prove active XMage untouched")
    require(prep.get("activation_allowed") is False, "Unexpected activation permission in previous gate")
    print("[OK] Controlled Install Prep V1 safety state verified")

    print("[STEP 1/3] Inspecting running XMage/Java process command lines...")
    process = powershell_process_hints()
    print(f"[INFO] Process path hints: {len(process)}")

    print("[STEP 2/3] Scanning filesystem for XMage client/launcher markers...")
    files = filesystem_hints()
    print(f"[INFO] Filesystem path hints: {len(files)}")

    candidates = roots_from_hints(process + files)
    active, evidence = resolve_single_candidate(candidates)
    print(f"[OK] Resolved active XMage root: {active}")
    print(f"[OK] Detection score: {evidence['score']}")

    OUT.mkdir(parents=True, exist_ok=True)
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = BACKUPS / f"XMage_ACTIVE_BACKUP_V3_{stamp}"

    print("[STEP 3/3] Creating full backup (candidate still BLOCKED)...")
    shutil.copytree(active, backup, copy_function=shutil.copy2)
    print("[STEP] Verifying source and backup SHA-256 trees...")
    src_hash, src_count, src_bytes = tree_digest(active)
    dst_hash, dst_count, dst_bytes = tree_digest(backup)
    require((src_hash, src_count, src_bytes) == (dst_hash, dst_count, dst_bytes), "Backup verification FAILED")
    print(f"[OK] Verified backup: {src_count} files, {src_bytes} bytes")
    print(f"[OK] Tree SHA-256: {src_hash}")

    rollback = OUT / "ROLLBACK_ACTIVE_XMAGE_V3.cmd"
    rollback.write_text(
        "@echo off\r\nsetlocal\r\n"
        "echo ============================================================\r\n"
        "echo XMage Community Patch - ROLLBACK ACTIVE XMAGE V3\r\n"
        "echo ============================================================\r\n"
        "echo VERIFIED BACKUP EXISTS. AUTOMATIC RESTORE IS NOT ARMED YET.\r\n"
        f"echo Active: {active}\r\n"
        f"echo Backup: {backup}\r\n"
        "echo Nothing is being restored or activated now.\r\n"
        "pause\r\n",
        encoding="utf-8",
    )

    data = {
        "schema": 3,
        "phase": "BACKUP_ROLLBACK_GATE_V3",
        "status": "VERIFIED_BACKUP_READY_ACTIVATION_STILL_BLOCKED",
        "active_xmage": str(active),
        "detection_score": evidence["score"],
        "detection_hints": evidence["hints"],
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
        "XMage Community Patch - BACKUP + ROLLBACK GATE V3\n"
        "==================================================\n\n"
        "RESULT: PASS\n"
        f"Active XMage: {active}\n"
        f"Detection score: {evidence['score']}\n"
        f"Verified backup: {backup}\n"
        f"Files: {src_count}\nBytes: {src_bytes}\nTree SHA-256: {src_hash}\n"
        "Backup verification: PASS\nRollback: PREPARED, NOT ARMED\n"
        "Candidate activation: BLOCKED\nActive XMage was NOT modified by this gate.\n",
        encoding="utf-8",
    )

    print("\n=== BACKUP + ROLLBACK GATE V3 PASSED ===")
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
        print("BACKUP + ROLLBACK GATE V3 STOPPED SAFELY. Candidate was NOT activated.")
        input("Press Enter to close...")
        raise SystemExit(1)
