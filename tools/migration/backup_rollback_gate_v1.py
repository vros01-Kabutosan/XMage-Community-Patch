#!/usr/bin/env python3
"""XMage Community Patch - BACKUP + ROLLBACK GATE V1.
Detects likely active XMage installations, but never modifies them.
Creates a verified backup only after a single unambiguous active installation is found.
No candidate activation occurs in this phase.
"""
from __future__ import annotations
import hashlib, json, os, shutil, sys, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
WORK=HERE/'migration-workspace'/'port-1.4.61V1'
CONTROL=WORK/'controlled-install-v1'
PREP=CONTROL/'CONTROLLED_INSTALL_PREP_V1.json'
OUT=WORK/'backup-rollback-gate-v1'
BACKUPS=OUT/'backups'
REPORT=OUT/'BACKUP_ROLLBACK_GATE_V1.json'
SUMMARY=OUT/'RESUMEN_BACKUP_ROLLBACK_GATE_V1.txt'

MARKERS=('startClient.bat','startClientWin7.bat')

def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def require(c,m):
 if not c: raise RuntimeError(m)

def candidate_roots():
 roots=[]
 env=os.environ
 for key in ('USERPROFILE','LOCALAPPDATA','APPDATA'):
  v=env.get(key)
  if v: roots.append(Path(v))
 for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
  p=Path(f'{letter}:/')
  if p.exists(): roots.append(p)
 # common names first, then shallow discovery only
 names=('xmage','XMage','mage','XMageLauncher')
 found=[]
 for root in roots:
  for n in names:
   p=root/n
   if p.is_dir(): found.append(p)
  try:
   for p in root.iterdir():
    if p.is_dir() and 'xmage' in p.name.lower(): found.append(p)
  except Exception: pass
 return list(dict.fromkeys(found))

def looks_active(p):
 if str(p).lower().find('migration-workspace')>=0: return False
 launcher=any((p/m).is_file() for m in MARKERS)
 jar=any((p/'lib').glob('mage-client*.jar')) if (p/'lib').is_dir() else False
 return launcher and jar

def tree_digest(root):
 h=hashlib.sha256(); count=0; total=0
 for p in sorted(x for x in root.rglob('*') if x.is_file()):
  rel=p.relative_to(root).as_posix().encode('utf-8','surrogatepass')
  h.update(rel); h.update(b'\0')
  s=p.stat().st_size; total+=s; count+=1
  h.update(str(s).encode()); h.update(b'\0'); h.update(sha256(p).encode()); h.update(b'\n')
 return h.hexdigest(),count,total

def main():
 print('=== XMage Community Patch - BACKUP + ROLLBACK GATE V1 ===')
 print('SAFE MODE: no candidate will be activated. Active XMage is read-only during detection.\n')
 require(PREP.is_file(),f'Missing controlled-install manifest: {PREP}')
 prep=json.loads(PREP.read_text(encoding='utf-8'))
 require(prep.get('status')=='CONTROLLED_INSTALL_READY_NOT_ACTIVATED','Controlled install V1 is not ready')
 require(prep.get('active_xmage_modified') is False,'Previous gate does not prove active XMage untouched')
 require(prep.get('activation_allowed') is False,'Unexpected activation permission in previous gate')
 print('[OK] Controlled Install Prep V1 safety state verified')

 found=[p.resolve() for p in candidate_roots() if looks_active(p)]
 found=list(dict.fromkeys(found))
 print(f'[INFO] Active XMage candidates found: {len(found)}')
 for i,p in enumerate(found,1): print(f'  {i}. {p}')
 require(len(found)==1,'Active XMage path is not unambiguous. Gate stopped; nothing was modified.')
 active=found[0]
 print(f'[OK] Unambiguous active XMage detected: {active}')

 OUT.mkdir(parents=True,exist_ok=True); BACKUPS.mkdir(parents=True,exist_ok=True)
 stamp=time.strftime('%Y%m%d-%H%M%S')
 backup=BACKUPS/f'XMage_ACTIVE_BACKUP_V1_{stamp}'
 print(f'[STEP] Creating full backup: {backup}')
 shutil.copytree(active,backup,copy_function=shutil.copy2)
 print('[STEP] Verifying complete backup tree (SHA-256 per file)...')
 src_hash,src_count,src_bytes=tree_digest(active)
 dst_hash,dst_count,dst_bytes=tree_digest(backup)
 require((src_hash,src_count,src_bytes)==(dst_hash,dst_count,dst_bytes),'Backup verification FAILED')
 print(f'[OK] Verified backup: {src_count} files, {src_bytes} bytes')
 print(f'[OK] Tree SHA-256: {src_hash}')

 rollback=OUT/'ROLLBACK_ACTIVE_XMAGE_V1.cmd'
 rollback.write_text('@echo off\r\nsetlocal\r\necho ============================================================\r\necho XMage Community Patch - ROLLBACK ACTIVE XMAGE V1\r\necho ============================================================\r\necho.\r\necho VERIFIED BACKUP EXISTS, but automatic restore is intentionally NOT ARMED.\r\necho Active path: '+str(active)+'\r\necho Backup path: '+str(backup)+'\r\necho.\r\necho The next activation gate must arm restoration only after final path checks.\r\necho Nothing is being restored now.\r\npause\r\n',encoding='utf-8')

 data={'schema':1,'phase':'BACKUP_ROLLBACK_GATE_V1','status':'VERIFIED_BACKUP_READY_ACTIVATION_STILL_BLOCKED','active_xmage':str(active),'backup':str(backup),'tree_sha256':src_hash,'files':src_count,'bytes':src_bytes,'backup_verified':True,'rollback_script':str(rollback),'rollback_armed':False,'candidate_activated':False,'active_xmage_modified_by_gate':False,'activation_allowed':False,'next_gate':'explicit controlled activation with preflight and armed rollback'}
 REPORT.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
 SUMMARY.write_text(f'XMage Community Patch - BACKUP + ROLLBACK GATE V1\n==================================================\n\nRESULT: PASS\nActive XMage: {active}\nVerified backup: {backup}\nFiles: {src_count}\nBytes: {src_bytes}\nTree SHA-256: {src_hash}\nBackup verification: PASS\nRollback script: PREPARED, NOT ARMED\nCandidate activation: BLOCKED\n\nThe active XMage installation was NOT modified by this gate.\n',encoding='utf-8')
 print('\n=== BACKUP + ROLLBACK GATE V1 PASSED ===')
 print(f'Backup: {backup}')
 print(f'Manifest: {REPORT}')
 print('Candidate activation remains BLOCKED. Active XMage was NOT modified by this gate.')
 return 0

if __name__=='__main__':
 try: sys.exit(main())
 except Exception as e:
  print(f'\nERROR: {e}')
  print('BACKUP + ROLLBACK GATE V1 STOPPED SAFELY. Candidate was NOT activated.')
  input('Press Enter to close...')
  sys.exit(1)
