#!/usr/bin/env python3
"""XMage Community Patch - POST ACTIVATION SMOKE V1.

Validates the real active XMage after CONTROLLED ACTIVATION V2.
This gate does not delete backups or old installations.

Checks:
- activation V2 manifest is in completed/post-smoke-required state;
- active XMage path is still the expected one;
- active client/runtime SHA-256 still match the verified candidate;
- launcher/runtime/config are present;
- previous installation and V4 verified backup still exist;
- optionally launches the real active client and asks for explicit visual smoke confirmation.

Only after all checks and user confirmation does this gate mark post activation smoke PASS.
Cleanup remains blocked for a later dedicated cleanup gate.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "migration-workspace" / "port-1.4.61V1"
ACTIVATION_DIR = WORK / "controlled-activation-v2"
ACTIVATION_MANIFEST = ACTIVATION_DIR / "CONTROLLED_ACTIVATION_V2.json"
OUT = WORK / "post-activation-smoke-v1"
REPORT = OUT / "POST_ACTIVATION_SMOKE_V1.json"
SUMMARY = OUT / "RESUMEN_POST_ACTIVATION_SMOKE_V1.txt"
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


def ask_yes_no(prompt: str) -> bool:
    while True:
        ans = input(prompt + " [Y/N]: ").strip().lower()
        if ans in ("y", "yes", "s", "si", "sí"):
            return True
        if ans in ("n", "no"):
            return False


def main() -> int:
    print("=== XMage Community Patch - POST ACTIVATION SMOKE V1 ===")
    print("This validates the REAL active 1.4.61V1 installation.")
    print("Backups will NOT be deleted by this gate.\n")

    act = load_json(ACTIVATION_MANIFEST)
    require(act.get("status") == "CONTROLLED_ACTIVATION_COMPLETED_POST_SMOKE_REQUIRED",
            "Controlled Activation V2 is not in post-smoke-required state")
    require(act.get("candidate_activated") is True,
            "Activation V2 does not report candidate as activated")
    require(act.get("post_activation_smoke_passed") is False,
            "Post activation smoke already marked passed")
    require(act.get("cleanup_allowed") is False,
            "Cleanup is unexpectedly allowed before smoke test")
    print("[OK] Controlled Activation V2 state verified")

    active = Path(str(act.get("active_xmage", "")))
    previous = Path(str(act.get("previous_installation_preserved", "")))
    backup = Path(str(act.get("verified_v4_backup_preserved", "")))
    rollback = Path(str(act.get("armed_rollback", "")))

    require(active.is_dir(), f"Active XMage missing: {active}")
    require(same_path(active, EXPECTED_ACTIVE),
            f"Active path changed: expected {EXPECTED_ACTIVE}, got {active}")
    require(previous.is_dir(), f"Immediate pre-activation installation missing: {previous}")
    require(backup.is_dir(), f"Verified V4 backup missing: {backup}")
    require(rollback.is_file(), f"Armed rollback script missing: {rollback}")
    print(f"[OK] Active path: {active}")
    print(f"[OK] Previous installation preserved: {previous}")
    print(f"[OK] V4 verified backup preserved: {backup}")
    print(f"[OK] Rollback still present: {rollback}")

    client = active / "lib" / "mage-client-1.4.61.jar"
    runtime = active / "config" / "deck-downloader" / "deck_library_updater.py"
    launcher = active / "startClient.bat"
    require(client.is_file(), f"Active client JAR missing: {client}")
    require(runtime.is_file(), f"Deck Downloader runtime missing: {runtime}")
    require(launcher.is_file(), f"Client launcher missing: {launcher}")

    client_hash = sha256(client)
    runtime_hash = sha256(runtime)
    require(client_hash == act.get("active_client_sha256_after"),
            "Active mage-client SHA-256 changed after activation")
    require(runtime_hash == act.get("active_runtime_sha256_after"),
            "Active Deck Downloader runtime SHA-256 changed after activation")
    print("[OK] Active client SHA-256 still matches activated candidate")
    print("[OK] Active Deck Downloader runtime SHA-256 still matches activated candidate")

    dck_root = active / "config" / "deck-downloader" / "MTGTop8" / "XMage_DCK"
    dck_counts = {}
    if dck_root.is_dir():
        for fmt in ("Standard", "Pioneer", "Modern"):
            folder = dck_root / fmt
            dck_counts[fmt.lower()] = len(list(folder.glob("*.dck"))) if folder.is_dir() else 0
        print(f"[INFO] Preserved DCK counts: Standard={dck_counts['standard']}, Pioneer={dck_counts['pioneer']}, Modern={dck_counts['modern']}")
    else:
        print("[WARN] Existing MTGTop8 DCK output folder not found in active tree; GUI/runtime smoke can still proceed")

    print("\n[GUI SMOKE] The active XMage client will now be launched from:")
    print(f"  {launcher}")
    print("When it opens, visually verify:")
    print("  1. XMage client reaches the normal main window without a startup error.")
    print("  2. The client shows version 1.4.61-V1 / 1.4.61V1 (or equivalent 1.4.61 build indication).")
    print("  3. Deck Editor can be opened.")
    print("  4. 'Descargar decks' / Deck Downloader can be opened without an immediate exception.")
    print("Leave XMage open while answering the questions below.\n")

    try:
        subprocess.Popen(["cmd", "/c", "start", "", str(launcher)], cwd=str(active))
    except Exception as exc:
        raise RuntimeError(f"Could not launch active XMage client: {exc}")

    require(ask_yes_no("Did the REAL active XMage GUI open normally?"),
            "User reported active XMage GUI smoke failure")
    require(ask_yes_no("Does it show the expected 1.4.61V1/1.4.61 build?"),
            "User reported unexpected XMage version after activation")
    require(ask_yes_no("Can Deck Editor be opened normally?"),
            "User reported Deck Editor smoke failure")
    require(ask_yes_no("Can Deck Downloader / Descargar decks be opened without an immediate error?"),
            "User reported Deck Downloader smoke failure")

    OUT.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": 1,
        "phase": "POST_ACTIVATION_SMOKE_V1",
        "status": "POST_ACTIVATION_SMOKE_PASSED_CLEANUP_STILL_BLOCKED",
        "active_xmage": str(active),
        "client_sha256": client_hash,
        "runtime_sha256": runtime_hash,
        "previous_installation_preserved": str(previous),
        "verified_v4_backup_preserved": str(backup),
        "rollback_script": str(rollback),
        "dck_counts": dck_counts,
        "gui_launch": "PASS_USER_CONFIRMED",
        "version_visual_check": "PASS_USER_CONFIRMED",
        "deck_editor_visual_check": "PASS_USER_CONFIRMED",
        "deck_downloader_visual_check": "PASS_USER_CONFIRMED",
        "post_activation_smoke_passed": True,
        "rollback_armed": True,
        "cleanup_allowed": False,
        "next_gate": "POST_ACTIVATION_FINALIZE_V1",
    }
    REPORT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    SUMMARY.write_text(
        "XMage Community Patch - POST ACTIVATION SMOKE V1\n"
        "=================================================\n\n"
        "RESULT: PASS\n"
        "Status: POST_ACTIVATION_SMOKE_PASSED_CLEANUP_STILL_BLOCKED\n"
        f"Active XMage: {active}\n"
        "Active client hash: PASS\n"
        "Deck Downloader runtime hash: PASS\n"
        "GUI launch: PASS (user confirmed)\n"
        "Version visual check: PASS (user confirmed)\n"
        "Deck Editor: PASS (user confirmed)\n"
        "Deck Downloader: PASS (user confirmed)\n"
        f"Previous installation preserved: {previous}\n"
        f"Verified V4 backup preserved: {backup}\n"
        "Rollback remains armed: YES\n"
        "Cleanup allowed: NO\n"
        "Next gate: POST_ACTIVATION_FINALIZE_V1\n",
        encoding="utf-8",
    )

    print("\n=== POST ACTIVATION SMOKE V1 PASSED ===")
    print("The active 1.4.61V1 installation passed static + GUI smoke checks.")
    print("Backups are STILL preserved. Cleanup remains blocked until FINALIZE V1.")
    print(f"Manifest: {REPORT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("POST ACTIVATION SMOKE V1 FAILED. DO NOT DELETE BACKUPS.")
        input("Press Enter to close...")
        raise SystemExit(1)
