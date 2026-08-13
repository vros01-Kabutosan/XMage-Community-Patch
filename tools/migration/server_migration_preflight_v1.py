#!/usr/bin/env python3
"""XMage Community Patch - SERVER MIGRATION PREFLIGHT V1.

SAFE MODE: does not replace the active server.
It identifies the active 1.4.60 server, finds the already-downloaded clean
1.4.61V1 server from migration-workspace/staging, verifies layout, and creates
a full verified backup plus a manifest for the next activation gate.
"""
from __future__ import annotations
import hashlib, json, os, shutil, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE/"migration-workspace"
WORK=ROOT/"server-port-1.4.61V1"
OUT=WORK/"preflight-v1"
REPORT=OUT/"SERVER_MIGRATION_PREFLIGHT_V1.json"
SUMMARY=OUT/"RESUMEN_SERVER_MIGRATION_PREFLIGHT_V1.txt"
ACTIVE=Path(r"J:\MTG\xmage\mage-server")


def require(c,m):
    if not c: raise RuntimeError(m)

def sha256(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def tree_digest(root):
    h=hashlib.sha256(); count=0; total=0
    for p in sorted((x for x in root.rglob('*') if x.is_file()), key=lambda x:str(x.relative_to(root)).lower()):
        rel=str(p.relative_to(root)).replace('\\','/').encode('utf-8')
        fh=sha256(p); size=p.stat().st_size
        h.update(rel+b'\0'+fh.encode()+b'\0'+str(size).encode()+b'\n')
        count+=1; total+=size
    return h.hexdigest(),count,total

def find_clean_server():
    candidates=[]
    staging=ROOT/"staging"
    if staging.is_dir():
        for p in staging.rglob('mage-server'):
            if p.is_dir():
                s=str(p).lower()
                score=0
                if '1.4.61' in s: score+=100
                if 'clean' in s: score+=60
                if 'staging' in s: score+=20
                if (p/'lib').is_dir(): score+=20
                if any((p/'lib').glob('mage-server*.jar')): score+=40
                if any((p/n).is_file() for n in ('startServer.bat','startServer.cmd')): score+=20
                candidates.append((score,p))
    # fallback: search the whole migration workspace, but heavily penalize old/community copies
    if not candidates:
        for p in ROOT.rglob('mage-server'):
            if p.is_dir():
                s=str(p).lower(); score=0
                if '1.4.61' in s: score+=100
                if 'clean' in s: score+=60
                if '1.4.60' in s or 'community' in s or 'backup' in s: score-=200
                if any((p/'lib').glob('mage-server*.jar')): score+=40
                candidates.append((score,p))
    require(candidates,'No candidate mage-server folder found in migration-workspace')
    candidates.sort(key=lambda x:x[0], reverse=True)
    best=candidates[0]
    require(best[0]>=100, f'No trustworthy clean 1.4.61 server candidate found. Best={best}')
    return best[1], candidates[:10]

def main():
    print('=== XMage Community Patch - SERVER MIGRATION PREFLIGHT V1 ===')
    print('SAFE MODE: active server will NOT be replaced.\n')
    require(ACTIVE.is_dir(), f'Active server not found: {ACTIVE}')
    active_jars=sorted((ACTIVE/'lib').glob('mage-server*.jar')) if (ACTIVE/'lib').is_dir() else []
    require(active_jars, 'Active server has no mage-server JAR')
    print(f'[OK] Active server found: {ACTIVE}')
    print(f'[INFO] Active server JAR: {active_jars[-1].name}')

    candidate, ranked=find_clean_server()
    cand_jars=sorted((candidate/'lib').glob('mage-server*.jar'))
    require(cand_jars, f'Candidate server has no mage-server JAR: {candidate}')
    require(candidate.resolve()!=ACTIVE.resolve(), 'Candidate unexpectedly equals active server')
    print(f'[OK] Clean 1.4.61 server candidate: {candidate}')
    print(f'[INFO] Candidate server JAR: {cand_jars[-1].name}')

    OUT.mkdir(parents=True,exist_ok=True)
    backups=WORK/'backups'; backups.mkdir(parents=True,exist_ok=True)
    backup=backups/f"mage-server-1.4.60V3-pre-1.4.61V1_{time.strftime('%Y%m%d-%H%M%S')}"
    print('[STEP 1/2] Creating full server backup...')
    shutil.copytree(ACTIVE,backup,copy_function=shutil.copy2)
    print('[STEP 2/2] Verifying full backup SHA-256 tree...')
    ah,ac,ab=tree_digest(ACTIVE); bh,bc,bb=tree_digest(backup)
    require((ah,ac,ab)==(bh,bc,bb),'Server backup SHA-256 tree verification failed')
    print(f'[OK] Verified server backup: {ac} files, {ab} bytes')
    print(f'[OK] Server backup tree SHA-256: {ah}')

    cand_hashes={p.name:sha256(p) for p in cand_jars}
    report={
      'schema':1,'phase':'SERVER_MIGRATION_PREFLIGHT_V1','status':'SERVER_1_4_61V1_READY_NOT_ACTIVATED',
      'active_server':str(ACTIVE),'active_server_jar':str(active_jars[-1]),
      'candidate_server':str(candidate),'candidate_server_jars':cand_hashes,
      'verified_backup':str(backup),'backup_tree_sha256':ah,'backup_files':ac,'backup_bytes':ab,
      'active_server_modified':False,'candidate_activated':False,'activation_allowed':True,
      'next_gate':'CONTROLLED_SERVER_ACTIVATION_V1'
    }
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    SUMMARY.write_text(
      'XMage Community Patch - SERVER MIGRATION PREFLIGHT V1\n'
      '=====================================================\n\n'
      'RESULT: PASS\n'
      f'Active server: {ACTIVE}\nCandidate server: {candidate}\nVerified backup: {backup}\n'
      f'Backup tree SHA-256: {ah}\nActive server modified: NO\nCandidate activated: NO\n'
      'Next gate: CONTROLLED_SERVER_ACTIVATION_V1\n',encoding='utf-8')
    print('\n=== SERVER MIGRATION PREFLIGHT V1 PASSED ===')
    print('Active server was NOT modified.')
    print(f'Manifest: {REPORT}')
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as e:
        print(f'\nERROR: {e}')
        print('SERVER MIGRATION PREFLIGHT V1 STOPPED SAFELY. Active server was NOT modified.')
        input('Press Enter to close...')
        raise SystemExit(1)
