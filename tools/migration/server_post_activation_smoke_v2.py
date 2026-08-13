#!/usr/bin/env python3
"""XMage Community Patch - SERVER POST ACTIVATION SMOKE V2.

V2 fixes the V1 smoke question being too strict/ambiguous about build times.
A client build timestamp and server build timestamp may differ, but the smoke
passes if both are 1.4.61-V1/1.4.61 and there is no Wrong client version error.

This gate does not delete backups and does not modify active files.
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
OUT = WORK / "server-post-activation-smoke-v2"
REPORT = OUT / "SERVER_POST_ACTIVATION_SMOKE_V2.json"
SUMMARY = OUT / "RESUMEN_SERVER_POST_ACTIVATION_SMOKE_V2.txt"
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


def ask_yes_no(prompt: str) -> bool:
    while True:
        ans = input(prompt + " [Y/N]: ").strip().lower()
        if ans in ("y", "yes", "s", "si", "sí"):
            return True
        if ans in ("n", "no"):
            return False


def same_path(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return str(a).lower() == str(b).lower()


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
    print("=== XMage Community Patch - SERVER POST ACTIVATION SMOKE V2 ===")
    print("SAFE MODE: this does NOT delete backups and does NOT modify active files.")
    print("V2 accepts client/server build timestamp drift if both are 1.4.61-V1/1.4.61.\n")

    act = load_json(ACTIVATION)
    require(act.get("status") == "CONTROLLED_SERVER_ACTIVATION_COMPLETED_POST_SMOKE_REQUIRED",
            "Controlled Server Activation V1 is not waiting for smoke test")
    require(act.get("candidate_activated") is True, "Server candidate was not activated")
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

    server_hashes = verify_server_hashes(active, expected_hashes)
    print("[OK] Active server JAR hash matches activated 1.4.61 candidate")

    require(EXPECTED_CLIENT.is_dir(), f"Active client missing: {EXPECTED_CLIENT}")
    client_jars = sorted((EXPECTED_CLIENT / "lib").glob("mage-client*.jar")) if (EXPECTED_CLIENT / "lib").is_dir() else []
    require(client_jars, f"No active mage-client JAR found in {EXPECTED_CLIENT}")
    print(f"[OK] Active client present: {EXPECTED_CLIENT}")
    print(f"[INFO] Active client JAR: {client_jars[-1].name}")

    require(INSTALLED_PROPERTIES.is_file(), f"installed.properties missing: {INSTALLED_PROPERTIES}")
    installed_text = INSTALLED_PROPERTIES.read_text(encoding="utf-8", errors="replace")
    require("1.4.61-dev (2026-08-12 12-34)" in installed_text,
            "installed.properties is not synchronized to 1.4.61-dev (2026-08-12 12-34)")
    print("[OK] Launcher installed.properties synchronized to 1.4.61")

    print("\n[REAL LAUNCHER SMOKE V2]")
    print("The XMage launcher will be opened now if possible.")
    print("In the launcher, click ONLY: Launch Client and Server. Do NOT click Update.")
    print("Smoke passes if:")
    print("  1. No 'Wrong client version' message appears.")
    print("  2. Client title shows 1.4.61-V1 or 1.4.61.")
    print("  3. Server title/status shows 1.4.61-V1 or 1.4.61.")
    print("  4. Build timestamps may differ; that is OK.")
    print("  5. The normal XMage screen is usable.\n")

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
    require(ask_yes_no("Does the CLIENT show 1.4.61-V1 or 1.4.61?"),
            "User reported unexpected client version")
    require(ask_yes_no("Does the SERVER show 1.4.61-V1 or 1.4.61, even if the build time differs from the client?"),
            "User reported unexpected server version")
    require(ask_yes_no("Can you use the normal XMage client screen after launching client and server?"),
            "User reported client/server smoke failure")

    OUT.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": 2,
        "phase": "SERVER_POST_ACTIVATION_SMOKE_V2",
        "status": "SERVER_POST_ACTIVATION_SMOKE_PASSED_CLEANUP_STILL_BLOCKED",
        "smoke_passed_at_local": datetime.now().astimezone().isoformat(),
        "active_server": str(active),
        "active_server_jars": server_hashes,
        "active_client": str(EXPECTED_CLIENT),
        "active_client_jar": str(client_jars[-1]),
        "installed_properties_synchronized": True,
        "wrong_client_version": "NOT_OBSERVED_USER_CONFIRMED",
        "client_version_visual_check": "1.4.61_PASS_USER_CONFIRMED",
        "server_version_visual_check": "1.4.61_PASS_USER_CONFIRMED_BUILD_TIME_DRIFT_ACCEPTED",
        "previous_server_preserved": str(previous),
        "verified_backup_preserved": str(backup),
        "rollback_script": str(rollback),
        "post_server_smoke_passed": True,
        "rollback_preserved": True,
        "cleanup_allowed": False,
        "known_remaining_blocker": "Deck Editor printing/image edition selector missing after 1.4.61V1 port",
        "next_gate": "SERVER_FINALIZE_V1_AFTER_SELECTOR_PORT_OR_ACKNOWLEDGED_BLOCKER",
    }
    REPORT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    SUMMARY.write_text(
        "XMage Community Patch - SERVER POST ACTIVATION SMOKE V2\n"
        "========================================================\n\n"
        "RESULT: PASS\n"
        "Status: SERVER_POST_ACTIVATION_SMOKE_PASSED_CLEANUP_STILL_BLOCKED\n"
        f"Active server: {active}\n"
        f"Active client: {EXPECTED_CLIENT}\n"
        "Wrong client version: NOT OBSERVED (user confirmed)\n"
        "Client version: 1.4.61 PASS\n"
        "Server version: 1.4.61 PASS\n"
        "Client/server build timestamp drift: ACCEPTED\n"
        f"Previous server preserved: {previous}\n"
        f"Verified backup preserved: {backup}\n"
        f"Rollback script: {rollback}\n"
        "Known remaining blocker: Deck Editor printing/image edition selector missing after 1.4.61V1 port\n"
        "Cleanup allowed: NO\n",
        encoding="utf-8",
    )

    print("\n=== SERVER POST ACTIVATION SMOKE V2 PASSED ===")
    print("Client and server are version-aligned at 1.4.61V1/1.4.61.")
    print("Build timestamp drift is accepted.")
    print("Known remaining blocker: Deck Editor printing/image edition selector missing.")
    print("Backups are still preserved. Cleanup remains blocked.")
    print(f"Manifest: {REPORT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("SERVER POST ACTIVATION SMOKE V2 FAILED. DO NOT DELETE BACKUPS.")
        input("Press Enter to close...")
        raise SystemExit(1)
