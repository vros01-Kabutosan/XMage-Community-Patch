#!/usr/bin/env python3
"""XMage Community Patch - CONTROLLED ACTIVATION V2.
V2 fixes V1's process detector false-positive: PowerShell used for inspection
could match the active XMage path embedded in its own command line.
"""
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
WORK=HERE/"migration-workspace"/"port-1.4.61V1"
PREFLIGHT_MANIFEST=WORK/"controlled-activation-preflight-v1"/"CONTROLLED_ACTIVATION_PREFLIGHT_V1.json"
OUT=WORK/"controlled-activation-v2"
REPORT=OUT/"CONTROLLED_ACTIVATION_V2.json"
SUMMARY=OUT/"RESUMEN_CONTROLLED_ACTIVATION_V2.txt"
EXPECTED_ACTIVE=Path(r"J:\MTG\xmage\mage-client")
BLOCKED_EXTENSIONS={".jar",".class",".exe",".dll",".so",".dylib",".bat",".cmd",".ps1",".sh",".py",".pyc",".pyo"}
BLOCKED_DIR_NAMES={"__pycache__",".git",".github","target","build"}

def sha256(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
 return h.hexdigest()
def require(c,m):
 if not c: raise RuntimeError(m)
def load_json(p): require(p.is_file(),f"Missing manifest: {p}"); return json.loads(p.read_text(encoding="utf-8"))
def same_path(a,b):
 try:return a.resolve()==b.resolve()
 except OSError:return str(a).lower()==str(b).lower()

def xmage_running_from(active):
 """Only consider plausible XMage/Java processes; exclude our PowerShell inspector."""
 active_s=str(active).replace("'","''")
 ps=("$ErrorActionPreference='Stop'; $me=$PID; "
     "Get-CimInstance Win32_Process | Where-Object { "
     "$_.ProcessId -ne $me -and $_.CommandLine -and "
     "$_.Name -match '^(java|javaw|XMageLauncher|cmd)\\.exe$' -and "
     f"$_.CommandLine -like '*{active_s}*' "
     "} | ForEach-Object { '{0}|{1}|{2}' -f $_.ProcessId,$_.Name,$_.CommandLine }")
 try:
  cp=subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command",ps],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",errors="replace",timeout=30)
  require(cp.returncode==0,"Process inspection failed: "+cp.stderr.strip())
  return [x.strip() for x in cp.stdout.splitlines() if x.strip()]
 except subprocess.TimeoutExpired: raise RuntimeError("Process inspection timed out; activation stopped safely")

def copy_candidate(candidate,stage):
 n=total=0
 for root,dirs,files in os.walk(candidate):
  sr=Path(root); dr=stage/sr.relative_to(candidate); dr.mkdir(parents=True,exist_ok=True)
  for name in files:
   s=sr/name; shutil.copy2(s,dr/name); n+=1; total+=s.stat().st_size
 return n,total
def should_preserve(rel): return not any(p.lower() in BLOCKED_DIR_NAMES for p in rel.parts) and rel.suffix.lower() not in BLOCKED_EXTENSIONS
def merge_user_data(active,stage):
 copied=existing=skipped=0
 for root,dirs,files in os.walk(active):
  sr=Path(root); rr=sr.relative_to(active); dirs[:]=[d for d in dirs if d.lower() not in BLOCKED_DIR_NAMES]
  for name in files:
   s=sr/name; rel=rr/name
   if not should_preserve(rel): skipped+=1; continue
   d=stage/rel
   if d.exists(): existing+=1; continue
   d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(s,d); copied+=1
 return copied,existing,skipped
def verify_stage(stage,p):
 client=stage/"lib"/"mage-client-1.4.61.jar"; runtime=stage/"config"/"deck-downloader"/"deck_library_updater.py"; launcher=stage/"startClient.bat"
 require(client.is_file(),f"Staging client missing: {client}"); require(runtime.is_file(),f"Runtime missing: {runtime}"); require(launcher.is_file(),f"Launcher missing: {launcher}")
 ch=sha256(client); rh=sha256(runtime)
 require(ch==p.get("candidate_client_sha256"),"Client SHA-256 differs from verified candidate")
 require(rh==p.get("candidate_runtime_sha256"),"Deck Downloader runtime SHA-256 differs from verified candidate")
 return {"client_sha256":ch,"runtime_sha256":rh}

def main():
 print("=== XMage Community Patch - CONTROLLED ACTIVATION V2 ===")
 print("V2: corrected process detector; PowerShell self-match eliminated.\n")
 p=load_json(PREFLIGHT_MANIFEST)
 require(p.get("status")=="READY_FOR_CONTROLLED_ACTIVATION","Preflight not ready")
 require(p.get("activation_allowed") is True and p.get("rollback_armed") is True,"Activation/rollback safety state invalid")
 require(p.get("candidate_activated") is False and p.get("active_xmage_modified_by_gate") is False,"Preflight state inconsistent")
 active=Path(str(p.get("active_xmage",""))); backup=Path(str(p.get("backup",""))); candidate=Path(str(p.get("controlled_candidate",""))); rollback=Path(str(p.get("rollback_script","")))
 require(active.is_dir() and same_path(active,EXPECTED_ACTIVE),f"Active XMage path invalid: {active}")
 require(backup.is_dir(),f"Backup missing: {backup}"); require(candidate.is_dir(),f"Candidate missing: {candidate}"); require(rollback.is_file(),f"Rollback missing: {rollback}")
 print("[OK] Preflight, active path, backup, candidate and rollback verified")
 running=xmage_running_from(active)
 if running:
  print("[BLOCK] Actual process(es) referencing active XMage:")
  for x in running: print("  "+x)
  raise RuntimeError("XMage/Java appears to be running. Close it and retry.")
 print("[OK] No real XMage/Java process references active path")
 parent=active.parent; stage=parent/(active.name+".ACTIVATION_STAGE_V2"); stamp=time.strftime("%Y%m%d-%H%M%S"); previous=parent/(active.name+f".PRE_ACTIVATION_V2_{stamp}")
 if stage.exists(): shutil.rmtree(stage)
 stage.mkdir(parents=True)
 print("[STEP 1/5] Building verified 1.4.61V1 staging tree..."); nf,nb=copy_candidate(candidate,stage); print(f"[OK] {nf} candidate files copied ({nb} bytes)")
 print("[STEP 2/5] Preserving non-code user data..."); preserved,existing,skipped=merge_user_data(active,stage); print(f"[OK] preserved={preserved}, candidate-owned={existing}, old-code-skipped={skipped}")
 print("[STEP 3/5] Verifying critical hashes..."); info=verify_stage(stage,p); print("[OK] Critical hashes match verified candidate")
 OUT.mkdir(parents=True,exist_ok=True)
 base={"schema":2,"phase":"CONTROLLED_ACTIVATION_V2","active_xmage":str(active),"verified_backup":str(backup),"armed_rollback":str(rollback),"candidate":str(candidate),"stage":str(stage),"previous_installation":str(previous),"candidate_files":nf,"candidate_bytes":nb,"user_data_preserved_files":preserved,"old_code_files_skipped":skipped,**info}
 REPORT.write_text(json.dumps({**base,"status":"STAGING_VERIFIED_SWAP_PENDING"},indent=2),encoding="utf-8")
 print("[STEP 4/5] Atomic activation swap...")
 try: active.rename(previous)
 except OSError as e: raise RuntimeError(f"Could not preserve current installation: {e}")
 try: stage.rename(active)
 except OSError as e:
  try: previous.rename(active)
  except OSError as r: raise RuntimeError(f"CRITICAL swap+restore failure. Original at {previous}. swap={e}; restore={r}")
  raise RuntimeError(f"Swap failed; original restored automatically: {e}")
 print("[STEP 5/5] Post-swap verification...")
 try: finalinfo=verify_stage(active,p)
 except Exception as e:
  failed=parent/(active.name+f".FAILED_ACTIVATION_V2_{stamp}")
  try: active.rename(failed); previous.rename(active)
  except OSError as r: raise RuntimeError(f"CRITICAL verification+restore failure: {e}; restore={r}; V4 backup={backup}")
  raise RuntimeError(f"Post-swap verification failed; old installation restored; failed candidate={failed}: {e}")
 final={**base,"status":"CONTROLLED_ACTIVATION_COMPLETED_POST_SMOKE_REQUIRED","active_client_sha256_after":finalinfo["client_sha256"],"active_runtime_sha256_after":finalinfo["runtime_sha256"],"previous_installation_preserved":str(previous),"verified_v4_backup_preserved":str(backup),"rollback_armed":True,"candidate_activated":True,"post_activation_smoke_passed":False,"cleanup_allowed":False,"next_gate":"POST_ACTIVATION_SMOKE_V1"}
 REPORT.write_text(json.dumps(final,indent=2),encoding="utf-8")
 SUMMARY.write_text(f"CONTROLLED ACTIVATION V2: PASS\nActive: {active}\nPrevious: {previous}\nV4 backup: {backup}\nRollback: {rollback}\nNext: POST_ACTIVATION_SMOKE_V1\n",encoding="utf-8")
 print("\n=== CONTROLLED ACTIVATION V2 COMPLETED ==="); print(f"Active: {active}"); print(f"Previous installation preserved: {previous}"); print(f"V4 backup preserved: {backup}"); print("DO NOT DELETE BACKUPS. Next: POST_ACTIVATION_SMOKE_V1.")
 return 0
if __name__=="__main__":
 try: raise SystemExit(main())
 except Exception as e:
  print(f"\nERROR: {e}"); print("CONTROLLED ACTIVATION V2 STOPPED/ROLLED BACK SAFELY WHERE POSSIBLE."); input("Press Enter to close..."); raise SystemExit(1)
