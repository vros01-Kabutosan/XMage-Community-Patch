#!/usr/bin/env python3
"""XMage Community Patch - SERVER POST ACTIVATION SMOKE V1.

Validates the active server after CONTROLLED SERVER ACTIVATION V1.
This gate does not delete backups and does not modify client/server files.
It performs static integrity checks and then guides a real launcher smoke test.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).resolve().parent
WORK = HERE / "migration-workspace" / "server-port-1.4.61V1"
ACTIVATION = WORK / "controlled-server-activation-v1" / "CONTROLLED_SERVER_ACTIVATION_V1.json"
OUT = WORK / "server-post-activation-smoke-v1"
REPORT = OUT / "SERVER_POST_ACTIVATION_SMOKE_V1.json"
SUMMARY = OUT / "RESUMEN_SERVER_POST_ACTIVATION_SMOKE_V1.txt"
EXPECTED_SERVER = Path(r"J:\MTG\xmage\mage-server")
EXPECTED_CLIENT = Path(r"J:\MTG\xmage\mage-client")
LAUNCHER = Path(r"J:\MTG\XMageLauncher-0.3.8.jar")
INSTALLED_PROPERTIES = Path(r"J:\MTG\installed.properties")


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


def ask_yes_no(prompt: str) -> bool:
    while True:
        ans = input(prompt + " [Y/N]: ").strip().lower()
        if ans in ("y", "yes", "s", "si", "sí"):
            return True
        if ans in ("n", "no"):
            return False


def verify_server_hashes(server: Path, expected_hashes: dict[str, str]) -> dict[str, str]:
    require(server.is_dir(), f"Active server folder missing: {server}")
    jars = sorted((server / "lib").glob("mage-server*.jar")) if (server / "lib").is_dir() else []
    require(jars, f"No active mage-server JAR found in {server}")
    found = {p.name: sha256(p) for p in jars}
    for name, digest in expected_hashes.items():
        require(name in found, f"Expected server JAR missing from active server: {name}")
        require(found[name] == digest, f"Active server JAR hash mismatch: {name}")
    return found


def main() -> int:
    print("=== XMage Community Patch - SERVER POST ACTIVATION SMOKE V1 ===")
    print("SAFE MODE: this does NOT delete backups and does NOT modify active files.\n")

    act = load_json(ACTIVATION)
    require(act.get("status") == "CONTROLLED_SERVER_ACTIVATION_COMPLETED_POST_SMOKE_REQUIRED",
            "Controlled Server Activation V1 is not waiting for smoke test")
    require(act.get("candidate_activated") is True, "Server candidate was not activated")
    require(act.get("post_server_smoke_passed") is False, "Server smoke is already marked as passed")
    require(act.get("cleanup_allowed") is False, "Cleanup unexpectedly allowed before smoke")

    active = Path(str(act.get("active_server", "")))
    previous = Path(str(act.get("previous_server", "")))
    backup = Path(str(act.get("verified_backup", "")))
    rollback = Path(str(act.get("rollback_script", "")))
    expected_hashes = dict(act.get("candidate_server_jars", {}))

    require(active.is_dir(), f"Active server missing: {active}")
    require(same_path(active, EXPECTED_SERVER), f"Unexpected active server path: {active}")
    require(previous.is_dir(), f"Previous server rollback folder missing: {previous}")
    require(backup.is_dir(), f"Verified server backup missing: {backup}")
    require(rollback.is_file(), f"Rollback script missing: {rollback}")
    require(expected_hashes, "Expected server hashes missing from activation manifest")

    print("[OK] Controlled Server Activation V1 manifest verified")
    print(f"[OK] Active server: {active}")
    print(f"[OK] Previous server preserved: {previous}")
    print(f"[OK] Verified preflight backup preserved: {backup}")
    print(f"[OK] Rollback script preserved: {rollback}")

    server_hashes = verify_server_hashes(active, expected_hashes)
    print("[OK] Active server JAR hash still matches activated candidate")

    require(EXPECTED_CLIENT.is_dir(), f"Active client missing: {EXPECTED_CLIENT}")
    client_jars = sorted((EXPECTED_CLIENT / "lib").glob("mage-client*.jar")) if (EXPECTED_CLIENT / "lib").is_dir() else []
    require(client_jars, f"No active mage-client JAR found in {EXPECTED_CLIENT}")
    print(f"[OK] Active client present: {EXPECTED_CLIENT}")
    print(f"[INFO] Active client JAR: {client_jars[-1].name}")

    require(INSTALLED_PROPERTIES.is_file(), f"installed.properties missing: {INSTALLED_PROPERTIES}")
    installed_text = INSTALLED_PROPERTIES.read_text(encoding="utf-8", errors="replace")
    require("1.4.61-dev (2026-08-12 12-34)" in installed_text,
            "installed.properties is not synchronized to 1.4.61-dev (2026-08-12 12-34)")
    print("[OK] Launcher installed.properties is synchronized to 1.4.61")

    print("\n[REAL LAUNCHER SMOKE]")
    print("The XMage launcher will be opened now.")
    print("In the launcher, click ONLY: Launch Client and Server")
    print("Do NOT click Update.")
    print("Then verify visually:")
    print("  1. No 'Wrong client version' message appears.")
    print("  2. Client shows 1.4.61-V1.")
    print("  3. Local server starts without version mismatch.")
    print("  4. You can reach the normal XMage client screen.")
    print("Leave the launcher/client/server open while answering below.\n")

    if LAUNCHER.is_file():
        try:
            subprocess.Popen(["cmd", "/c", "start", "", "java", "-jar", str(LAUNCHER)], cwd=str(LAUNCHER.parent))
        except Exception as exc:
            print(f"[WARN] Could not auto-launch XMage launcher: {exc}")
            print(f"Open it manually: {LAUNCHER}")
    else:
        print(f"[WARN] Launcher not found at {LAUNCHER}; open your normal launcher manually.")

    require(ask_yes_no("Did Launch Client and Server open without 'Wrong client version'?"),
            "User reported version mismatch still present")
    require(ask_yes_no("Does the client show 1.4.61-V1 / build 2026-08-12 20:03 or equivalent 1.4.61 build?"),
            "User reported unexpected client version")
    require(ask_yes_no("Did the local server start normally without immediate crash/error?"),
            "User reported local server startup failure")
    require(ask_yes_no("Can you use the normal XMage client screen after launching client and server?"),
            "User reported client/server smoke failure")

    OUT.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": 1,
        "phase": "SERVER_POST_ACTIVATION_SMOKE_V1",
        "status": "SERVER_POST_ACTIVATION_SMOKE_PASSED_CLEANUP_STILL_BLOCKED",
        "smoke_passed_at_local": datetime.now().astimezone().isoformat(),
        "active_server": str(active),
        "active_server_jars": server_hashes,
        "active_client": str(EXPECTED_CLIENT),
        "active_client_jar": str(client_jars[-1]),
        "installed_properties_synchronized": True,
        "wrong_client_version": "NOT_OBSERVED_USER_CONFIRMED",
        "client_version_visual_check": "PASS_USER_CONFIRMED",
        "local_server_start_visual_check": "PASS_USER_CONFIRMED",
        "previous_server_preserved": str(previous),
        "verified_backup_preserved": str(backup),
        "rollback_script": str(rollback),
        "post_server_smoke_passed": True,
        "rollback_preserved": True,
        "cleanup_allowed": False,
        "next_gate": "SERVER_FINALIZE_V1",
    }
    REPORT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    SUMMARY.write_text(
        "XMage Community Patch - SERVER POST ACTIVATION SMOKE V1\n"
        "========================================================\n\n"
        "RESULT: PASS\n"
        "Status: SERVER_POST_ACTIVATION_SMOKE_PASSED_CLEANUP_STILL_BLOCKED\n"
        f"Active server: {active}\n"
        f"Active client: {EXPECTED_CLIENT}\n"
        "Wrong client version: NOT OBSERVED (user confirmed)\n"
        "Client version visual check: PASS\n"
        "Local server startup: PASS\n"
        f"Previous server preserved: {previous}\n"
        f"Verified backup preserved: {backup}\n"
        f"Rollback script: {rollback}\n"
        "Cleanup allowed: NO\n"
        "Next gate: SERVER_FINALIZE_V1\n",
        encoding="utf-8",
    )

    print("\n=== SERVER POST ACTIVATION SMOKE V1 PASSED ===")
    print("Client and server are now version-aligned at 1.4.61V1/1.4.61.")
    print("Backups are still preserved. Cleanup remains blocked until finalization.")
    print(f"Manifest: {REPORT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("SERVER POST ACTIVATION SMOKE V1 FAILED. DO NOT DELETE BACKUPS.")
        input("Press Enter to close...")
        raise SystemExit(1)
