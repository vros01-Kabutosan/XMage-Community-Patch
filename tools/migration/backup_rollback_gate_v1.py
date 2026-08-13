#!/usr/bin/env python3
"""XMage Community Patch - BACKUP + ROLLBACK GATE V2.
Robustly discovers nested Windows XMage installations, never activates candidate,
and creates a verified backup only after one unambiguous active installation is found.
"""
from __future__ import annotations
import hashlib, json, os, shutil, sys, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
WORK=HERE/'migration-workspace'/'port-1.4.61V1'
CONTROL=WORK/'controlled-install-v1'
PREP=CONTROL/'CONTROLLED_INSTALL_PREP_V1.json'
OUT=WORK/'backup-rollback-gate-v2'
BACKUPS=OUT/'backups'
REPORT=OUT/'BACKUP_ROLLBACK_GATE_V2.json'
SUMMARY=OUT/'RESUMEN_BACKUP_ROLLBACK_GATE_V2.txt'
MARKERS=('startClient.bat','startClientWin7.bat','startClient.cmd','startClientWin7.cmd')
SKIP=('migration-workspace','xmage-community-patch','system volume information','$recycle.bin','windows','program files','program files (x86)')

def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def require(c,m):
 if not c: raise RuntimeError(m)

def looks_active(p):
 s=str(p).lower()
 if any(x in s for x in ('migration-workspace','xmage-community-patch')): return False
 launcher=any((p/m).is_file() for m in MARKERS)
 lib=p/'lib'
 jar=lib.is_dir() and any(lib.glob('mage-client*.jar'))
 return launcher and jar

def scan_base(base,max_depth=5):
 hits=[]
 if not base.exists(): return hits
 base=base.resolve()
 stack=[(base,0)]
 seen=set()
 while stack:
  p,d=stack.pop()
  key=str(p).lower()
  if key in seen: continue
  seen.add(key)
  try:
   if looks_active(p): hits.append(p); continue
   if d>=max_depth: continue
   for c in p.iterdir():
    if not c.is_dir(): continue
    n=c.name.lower()
    if n in SKIP or n.startswith('$'): continue
    # prioritize plausible XMage/launcher/version dirs, but descend generally on user/data drives
    stack.append((c,d+1))
  except (PermissionError,OSError): pass
 return hits

def candidate_roots():
 bases=[]
 for key in ('USERPROFILE','LOCALAPPDATA','APPDATA'):
  v=os.environ.get(key)
  if v: bases.append(Path(v))
 for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
  p=Path(f'{letter}:/')
  if p.exists(): bases.append(p)
 found=[]
 for b in bases:
  found.extend(scan_base(b,5))
 # de-duplicate aliases and nested duplicates
 uniq=[]; seen=set()
 for p in found:
  try: r=p.resolve()
  except OSError: r=p
  k=str(r).lower()
  if k not in seen: seen.add(k); uniq.append(r)
 return uniq

def tree_digest(root):
 h=hashlib.sha256(); count=0; total=0
 for p in sorted(x for x in root.rglob('*') if x.is_file()):
  rel=p.relative_to(root).as_posix().encode('utf-8','surrogatepass')
  h.update(rel); h.update(b'\0'); s=p.stat().st_size; total+=s; count+=1
  h.update(str(s).encode()); h.update(b'\0'); h.update(sha256(p).encode()); h.update(b'\n')
 return h.hexdigest(),count,total

def main():
 print('=== XMage Community Patch - BACKUP + ROLLBACK GATE V2 ===')
 print('SAFE MODE: candidate activation remains BLOCKED. Detection is read-only.\n')
 require(PREP.is_file(),f'Missing controlled-install manifest: {PREP}')
 prep=json.loads(PREP.read_text(encoding='utf-8'))
 require(prep.get('status')=='CONTROLLED_INSTALL_READY_NOT_ACTIVATED','Controlled Install Prep V1 is not ready')
 require(prep.get('active_xmage_modified') is False,'Previous gate does not prove active XMage untouched')
 require(prep.get('activation_allowed') is False,'Unexpected activation permission in previous gate')
 print('[OK] Controlled Install Prep V1 safety state verified')
 print('[STEP] Searching Windows drives for the real active XMage client...')
 found=candidate_roots()
 print(f'[INFO] Active XMage candidates found: {len(found)}')
 for i,p in enumerate(found,1): print(f'  {i}. {p}')
 require(len(found)==1,'Active XMage path is not unambiguous. Gate stopped; nothing was modified.')
 active=found[0]
 print(f'[OK] Unambiguous active XMage detected: {active}')
 OUT.mkdir(parents=True,exist_ok=True); BACKUPS.mkdir(parents=True,exist_ok=True)
 stamp=time.strftime('%Y%m%d-%H%M%S'); backup=BACKUPS/f'XMage_ACTIVE_BACKUP_V2_{stamp}'
 print(f'[STEP] Creating full verified backup: {backup}')
 shutil.copytree(active,backup,copy_function=shutil.copy2)
 print('[STEP] Verifying source and backup SHA-256 trees...')
 a,ac,ab=tree_digest(active); b,bc,bb=tree_digest(backup)
 require((a,ac,ab)==(b,bc,bb),'Backup verification FAILED')
 print(f'[OK] Verified backup: {ac} files, {ab} bytes')
 print(f'[OK] Tree SHA-256: {a}')
 rollback=OUT/'ROLLBACK_ACTIVE_XMAGE_V2.cmd'
 rollback.write_text('@echo off\r\nsetlocal\r\necho XMage Community Patch - ROLLBACK ACTIVE XMAGE V2\r\necho.\r\necho VERIFIED BACKUP EXISTS. AUTOMATIC RESTORE IS NOT ARMED YET.\r\necho Active: '+str(active)+'\r\necho Backup: '+str(backup)+'\r\necho.\r\necho Nothing is being restored or activated now.\r\npause\r\n',encoding='utf-8')
 data={'schema':2,'phase':'BACKUP_ROLLBACK_GATE_V2','status':'VERIFIED_BACKUP_READY_ACTIVATION_STILL_BLOCKED','active_xmage':str(active),'backup':str(backup),'tree_sha256':a,'files':ac,'bytes':ab,'backup_verified':True,'rollback_script':str(rollback),'rollback_armed':False,'candidate_activated':False,'active_xmage_modified_by_gate':False,'activation_allowed':False}
 REPORT.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
 SUMMARY.write_text(f'XMage Community Patch - BACKUP + ROLLBACK GATE V2\nRESULT: PASS\nActive XMage: {active}\nVerified backup: {backup}\nFiles: {ac}\nBytes: {ab}\nTree SHA-256: {a}\nCandidate activation: BLOCKED\n',encoding='utf-8')
 print('\n=== BACKUP + ROLLBACK GATE V2 PASSED ===')
 print(f'Active XMage: {active}\nBackup: {backup}\nManifest: {REPORT}')
 print('Candidate activation remains BLOCKED. Active XMage was NOT modified by this gate.')
 return 0

if __name__=='__main__':
 try: sys.exit(main())
 except Exception as e:
  print(f'\nERROR: {e}\nBACKUP + ROLLBACK GATE V2 STOPPED SAFELY. Candidate was NOT activated.')
  input('Press Enter to close...'); sys.exit(1)
