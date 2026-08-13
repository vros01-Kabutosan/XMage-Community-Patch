#!/usr/bin/env python3
"""XMage Community Patch - POST ACTIVATION FINALIZE V1.

Final bookkeeping gate after POST ACTIVATION SMOKE V1 PASS.
It does NOT delete backups, old installations, images, decks, or rollback data.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "migration-workspace" / "port-1.4.61V1"
ACT = WORK / "controlled-activation-v2" / "CONTROLLED_ACTIVATION_V2.json"
SMOKE = WORK / "post-activation-smoke-v1" / "POST_ACTIVATION_SMOKE_V1.json"
OUT = WORK / "post-activation-finalize-v1"
REPORT = OUT / "POST_ACTIVATION_FINALIZE_V1.json"
SUMMARY = OUT / "RESUMEN_POST_ACTIVATION_FINALIZE_V1.txt"
EXPECTED_ACTIVE = Path(r"J:\MTG\xmage\mage-client")

def require(c, m):
    if not c: raise RuntimeError(m)

def load(p):
    require(p.is_file(), f"Missing required manifest: {p}")
    return json.loads(p.read_text(encoding="utf-8"))

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def main():
    print("=== XMage Community Patch - POST ACTIVATION FINALIZE V1 ===")
    print("SAFE FINALIZE: no backups, images, decks or rollback data will be deleted.\n")
    act=load(ACT); smoke=load(SMOKE)
    require(act.get("status")=="CONTROLLED_ACTIVATION_COMPLETED_POST_SMOKE_REQUIRED", "Activation V2 state invalid")
    require(act.get("candidate_activated") is True, "Candidate was not activated")
    require(smoke.get("status")=="POST_ACTIVATION_SMOKE_PASSED_CLEANUP_STILL_BLOCKED", "Post activation smoke did not PASS")
    require(smoke.get("post_activation_smoke_passed") is True, "Smoke PASS flag missing")
    print("[OK] Controlled Activation V2 manifest verified")
    print("[OK] POST ACTIVATION SMOKE V1 PASS verified")

    active=Path(smoke["active_xmage"])
    require(active.is_dir(), f"Active XMage missing: {active}")
    require(str(active).lower()==str(EXPECTED_ACTIVE).lower(), f"Unexpected active path: {active}")
    client=active/"lib"/"mage-client-1.4.61.jar"
    runtime=active/"config"/"deck-downloader"/"deck_library_updater.py"
    require(client.is_file() and runtime.is_file(), "Critical active files missing")
    ch=sha256(client); rh=sha256(runtime)
    require(ch==smoke.get("client_sha256"), "Active client changed since smoke PASS")
    require(rh==smoke.get("runtime_sha256"), "Deck Downloader runtime changed since smoke PASS")
    print("[OK] Active client hash unchanged since smoke PASS")
    print("[OK] Deck Downloader runtime hash unchanged since smoke PASS")

    previous=Path(smoke["previous_installation_preserved"])
    backup=Path(smoke["verified_v4_backup_preserved"])
    rollback=Path(smoke["rollback_script"])
    require(previous.is_dir(), "Pre-activation installation backup missing")
    require(backup.is_dir(), "Verified V4 backup missing")
    require(rollback.is_file(), "Rollback script missing")
    print("[OK] Immediate pre-activation installation remains preserved")
    print("[OK] Verified V4 backup remains preserved")
    print("[OK] Rollback remains available")

    counts=smoke.get("dck_counts", {})
    print(f"[INFO] Preserved DCK record: Standard={counts.get('standard','?')}, Pioneer={counts.get('pioneer','?')}, Modern={counts.get('modern','?')}")

    OUT.mkdir(parents=True, exist_ok=True)
    result={
      "schema":1,
      "phase":"POST_ACTIVATION_FINALIZE_V1",
      "status":"MIGRATION_1_4_61V1_FINALIZED_SUCCESSFULLY",
      "finalized_at_local":datetime.now().astimezone().isoformat(),
      "active_xmage":str(active),
      "client_sha256":ch,
      "runtime_sha256":rh,
      "post_activation_smoke":"PASS",
      "previous_installation_preserved":str(previous),
      "verified_v4_backup_preserved":str(backup),
      "rollback_script":str(rollback),
      "rollback_preserved":True,
      "backups_preserved":True,
      "cleanup_performed":False,
      "migration_complete":True,
      "recommendation":"Keep at least one verified rollback backup until the release has been used normally for a while."
    }
    REPORT.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    SUMMARY.write_text(
      "XMage Community Patch - POST ACTIVATION FINALIZE V1\n"
      "====================================================\n\n"
      "RESULT: PASS\n"
      "MIGRATION 1.4.61V1 FINALIZED SUCCESSFULLY\n\n"
      f"Active XMage: {active}\n"
      "Controlled Activation V2: PASS\n"
      "Post Activation Smoke V1: PASS\n"
      "Active client integrity: PASS\n"
      "Deck Downloader runtime integrity: PASS\n"
      "Backups preserved: YES\nRollback preserved: YES\nCleanup performed: NO\n\n"
      "The migration is complete. Keep at least one verified rollback backup until the release has been used normally for a while.\n",
      encoding="utf-8")
    print("\n=== POST ACTIVATION FINALIZE V1 PASSED ===")
    print("MIGRATION 1.4.61V1 FINALIZED SUCCESSFULLY.")
    print(f"Active XMage: {active}")
    print("Backups preserved: YES")
    print("Rollback preserved: YES")
    print("Cleanup performed: NO")
    print(f"Manifest: {REPORT}")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as e:
        print(f"\nERROR: {e}")
        print("FINALIZE V1 FAILED. Nothing was intentionally deleted. Keep all backups.")
        input("Press Enter to close...")
        raise SystemExit(1)
