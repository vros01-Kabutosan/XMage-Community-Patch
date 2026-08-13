#!/usr/bin/env python3
"""XMage Community Patch - CONTROLLED ACTIVATION V1.

This is the first gate that is allowed to replace the active XMage client.
It requires CONTROLLED_ACTIVATION_PREFLIGHT_V1 == READY_FOR_CONTROLLED_ACTIVATION.

Safety model:
1. Refuse to run if XMage appears to be running from the active path.
2. Build a NEW staging installation from the already-verified 1.4.61V1 candidate.
3. Carry forward user data from the current installation without carrying old
   executable/code artifacts into the new version.
4. Re-verify candidate client/runtime SHA-256 inside staging.
5. Atomically rename the old active installation aside and staging into place.
6. Keep BOTH the earlier verified V4 backup and the immediate pre-activation
   installation until the post-activation smoke gate passes.

No images/decks are hashed again in this gate; the V4 full backup already proved
those bytes were backed up. They are copied/preserved as user data.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "migration-workspace" / "port-1.4.61V1"
PREFLIGHT_DIR = WORK / "controlled-activation-preflight-v1"
PREFLIGHT_MANIFEST = PREFLIGHT_DIR / "CONTROLLED_ACTIVATION_PREFLIGHT_V1.json"
OUT = WORK / "controlled-activation-v1"
REPORT = OUT / "CONTROLLED_ACTIVATION_V1.json"
SUMMARY = OUT / "RESUMEN_CONTROLLED_ACTIVATION_V1.txt"

EXPECTED_ACTIVE = Path(r"J:\MTG\xmage\mage-client")

# Never carry code/binary artifacts from 1.4.60V3 into the new 1.4.61V1 tree.
BLOCKED_EXTENSIONS = {
    ".jar", ".class", ".exe", ".dll", ".so", ".dylib",
    ".bat", ".cmd", ".ps1", ".sh", ".py", ".pyc", ".pyo",
}
BLOCKED_DIR_NAMES = {
    "__pycache__", ".git", ".github", "target", "build"
}


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


def xmage_running_from(active: Path) -> list[str]:
    """Read-only process check. Returns command lines referencing active XMage."""
    active_s = str(active).replace("'", "''")
    ps = (
        "$ErrorActionPreference='SilentlyContinue'; "
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and "
        f"$_.CommandLine -like '*{active_s}*' }} | ForEach-Object {{ $_.CommandLine }}"
    )
    try:
        cp = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
        return [line.strip() for line in cp.stdout.splitlines() if line.strip()]
    except Exception:
        # If process inspection itself fails, fail closed later rather than guessing.
        return ["PROCESS_INSPECTION_FAILED"]


def copy_candidate(candidate: Path, stage: Path) -> tuple[int, int]:
    count = 0
    total = 0
    for root, dirs, files in os.walk(candidate):
        src_root = Path(root)
        rel_root = src_root.relative_to(candidate)
        dst_root = stage / rel_root
        dst_root.mkdir(parents=True, exist_ok=True)
        for name in files:
            src = src_root / name
            dst = dst_root / name
            shutil.copy2(src, dst)
            count += 1
            total += src.stat().st_size
    return count, total


def should_preserve(rel: Path) -> bool:
    if any(part.lower() in BLOCKED_DIR_NAMES for part in rel.parts):
        return False
    if rel.suffix.lower() in BLOCKED_EXTENSIONS:
        return False
    return True


def merge_user_data(active: Path, stage: Path) -> tuple[int, int, int]:
    """Copy non-code files missing from candidate; candidate files always win."""
    copied = 0
    skipped_existing = 0
    skipped_code = 0
    for root, dirs, files in os.walk(active):
        src_root = Path(root)
        rel_root = src_root.relative_to(active)
        dirs[:] = [d for d in dirs if d.lower() not in BLOCKED_DIR_NAMES]
        for name in files:
            src = src_root / name
            rel = rel_root / name
            if not should_preserve(rel):
                skipped_code += 1
                continue
            dst = stage / rel
            if dst.exists():
                skipped_existing += 1
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
    return copied, skipped_existing, skipped_code


def verify_stage(stage: Path, preflight: dict) -> dict:
    client = stage / "lib" / "mage-client-1.4.61.jar"
    runtime = stage / "config" / "deck-downloader" / "deck_library_updater.py"
    launcher = stage / "startClient.bat"
    require(client.is_file(), f"Staging client missing: {client}")
    require(runtime.is_file(), f"Staging Deck Downloader runtime missing: {runtime}")
    require(launcher.is_file(), f"Staging client launcher missing: {launcher}")
    client_hash = sha256(client)
    runtime_hash = sha256(runtime)
    require(client_hash == preflight.get("candidate_client_sha256"),
            "Staging client SHA-256 differs from verified preflight candidate")
    require(runtime_hash == preflight.get("candidate_runtime_sha256"),
            "Staging Deck Downloader runtime SHA-256 differs from verified preflight candidate")
    return {
        "client": str(client),
        "client_sha256": client_hash,
        "runtime": str(runtime),
        "runtime_sha256": runtime_hash,
        "launcher": str(launcher),
    }


def main() -> int:
    print("=== XMage Community Patch - CONTROLLED ACTIVATION V1 ===")
    print("WARNING: this gate CAN replace the active XMage client after all checks pass.\n")

    preflight = load_json(PREFLIGHT_MANIFEST)
    require(preflight.get("status") == "READY_FOR_CONTROLLED_ACTIVATION",
            "Activation preflight is not READY_FOR_CONTROLLED_ACTIVATION")
    require(preflight.get("activation_allowed") is True,
            "Activation preflight did not explicitly allow activation")
    require(preflight.get("rollback_armed") is True,
            "Rollback is not armed")
    require(preflight.get("candidate_activated") is False,
            "Candidate is already marked activated")
    require(preflight.get("active_xmage_modified_by_gate") is False,
            "Preflight unexpectedly modified active XMage")
    print("[OK] CONTROLLED ACTIVATION PREFLIGHT V1 state verified")

    active = Path(str(preflight.get("active_xmage", "")))
    backup = Path(str(preflight.get("backup", "")))
    candidate = Path(str(preflight.get("controlled_candidate", "")))
    rollback = Path(str(preflight.get("rollback_script", "")))

    require(active.is_dir(), f"Active XMage missing: {active}")
    require(same_path(active, EXPECTED_ACTIVE),
            f"Active path changed: expected {EXPECTED_ACTIVE}, got {active}")
    require(backup.is_dir(), f"Verified V4 backup missing: {backup}")
    require(candidate.is_dir(), f"Controlled candidate missing: {candidate}")
    require(rollback.is_file(), f"Armed rollback script missing: {rollback}")
    print(f"[OK] Active path: {active}")
    print(f"[OK] Verified backup: {backup}")
    print(f"[OK] Candidate: {candidate}")
    print(f"[OK] Armed rollback: {rollback}")

    running = xmage_running_from(active)
    require(not running,
            "XMage appears to be running from the active path. Close client/server/launcher and retry.")
    print("[OK] No running process references the active XMage path")

    parent = active.parent
    stage = parent / (active.name + ".ACTIVATION_STAGE_V1")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    previous = parent / (active.name + f".PRE_ACTIVATION_V1_{stamp}")

    require(not previous.exists(), f"Unexpected previous-folder collision: {previous}")
    if stage.exists():
        print(f"[CLEAN] Removing stale activation stage: {stage}")
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    print("[STEP 1/5] Building clean 1.4.61V1 staging tree from verified candidate...")
    candidate_files, candidate_bytes = copy_candidate(candidate, stage)
    print(f"[OK] Candidate copied: {candidate_files} files, {candidate_bytes} bytes")

    print("[STEP 2/5] Preserving non-code user data from current XMage...")
    preserved, existing, code_skipped = merge_user_data(active, stage)
    print(f"[OK] User-data files preserved: {preserved}")
    print(f"[INFO] Candidate-owned files kept: {existing}")
    print(f"[INFO] Old executable/code files deliberately not carried forward: {code_skipped}")

    print("[STEP 3/5] Verifying staging critical hashes...")
    stage_info = verify_stage(stage, preflight)
    print("[OK] Staging client SHA-256 matches verified candidate")
    print("[OK] Staging Deck Downloader runtime SHA-256 matches verified candidate")

    # Persist a pre-swap report before touching active path.
    OUT.mkdir(parents=True, exist_ok=True)
    pre_swap = {
        "schema": 1,
        "phase": "CONTROLLED_ACTIVATION_V1",
        "status": "STAGING_VERIFIED_SWAP_PENDING",
        "active_xmage": str(active),
        "verified_backup": str(backup),
        "armed_rollback": str(rollback),
        "candidate": str(candidate),
        "stage": str(stage),
        "previous_installation": str(previous),
        "candidate_files": candidate_files,
        "candidate_bytes": candidate_bytes,
        "user_data_preserved_files": preserved,
        "candidate_owned_existing_files": existing,
        "old_code_files_skipped": code_skipped,
        **stage_info,
    }
    REPORT.write_text(json.dumps(pre_swap, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[STEP 4/5] Atomic swap: preserving current installation beside the new one...")
    try:
        active.rename(previous)
    except OSError as exc:
        raise RuntimeError(f"Could not rename active XMage. Is something still using it? {exc}")

    try:
        stage.rename(active)
    except OSError as exc:
        print("[EMERGENCY] New staging could not be moved into active path; restoring old installation...")
        try:
            previous.rename(active)
        except OSError as restore_exc:
            raise RuntimeError(
                f"CRITICAL swap failure and emergency restore failed. "
                f"Original remains at {previous}. Swap error={exc}; restore error={restore_exc}"
            )
        raise RuntimeError(f"Activation swap failed; original installation restored automatically: {exc}")

    print("[STEP 5/5] Post-swap critical verification...")
    try:
        active_info = verify_stage(active, preflight)
    except Exception as exc:
        print("[EMERGENCY] Post-swap verification failed. Restoring previous installation...")
        failed = parent / (active.name + f".FAILED_ACTIVATION_V1_{stamp}")
        try:
            active.rename(failed)
            previous.rename(active)
        except OSError as restore_exc:
            raise RuntimeError(
                f"CRITICAL post-swap failure and automatic restore failed. "
                f"Verification={exc}; restore={restore_exc}; verified V4 backup remains at {backup}"
            )
        raise RuntimeError(
            f"Post-swap verification failed; previous installation restored. Failed candidate kept at {failed}: {exc}"
        )

    final = {
        **pre_swap,
        "status": "CONTROLLED_ACTIVATION_COMPLETED_POST_SMOKE_REQUIRED",
        "active_client_sha256_after": active_info["client_sha256"],
        "active_runtime_sha256_after": active_info["runtime_sha256"],
        "previous_installation_preserved": str(previous),
        "verified_v4_backup_preserved": str(backup),
        "rollback_armed": True,
        "candidate_activated": True,
        "post_activation_smoke_passed": False,
        "cleanup_allowed": False,
        "next_gate": "POST_ACTIVATION_SMOKE_V1",
    }
    REPORT.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")

    SUMMARY.write_text(
        "XMage Community Patch - CONTROLLED ACTIVATION V1\n"
        "================================================\n\n"
        "RESULT: ACTIVATION COMPLETED\n"
        "Status: CONTROLLED_ACTIVATION_COMPLETED_POST_SMOKE_REQUIRED\n"
        f"Active XMage: {active}\n"
        f"Previous installation preserved: {previous}\n"
        f"Verified V4 backup preserved: {backup}\n"
        f"Armed rollback: {rollback}\n"
        f"User-data files carried forward: {preserved}\n"
        "New client SHA-256: PASS\n"
        "Deck Downloader runtime SHA-256: PASS\n"
        "Cleanup allowed: NO\n"
        "Next gate: POST_ACTIVATION_SMOKE_V1\n",
        encoding="utf-8",
    )

    print("\n=== CONTROLLED ACTIVATION V1 COMPLETED ===")
    print(f"New active XMage: {active}")
    print(f"Previous installation preserved: {previous}")
    print(f"Verified V4 backup preserved: {backup}")
    print(f"Rollback remains armed: {rollback}")
    print("DO NOT delete backups yet. Next gate is POST_ACTIVATION_SMOKE_V1.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("CONTROLLED ACTIVATION V1 STOPPED/ROLLED BACK SAFELY WHERE POSSIBLE.")
        input("Press Enter to close...")
        raise SystemExit(1)
