#!/usr/bin/env python3
"""Capture the RC1 Deck Downloader runtime/config into one auditable ZIP.

SAFE MODE: reads migration-workspace/community snapshot and writes reports only.
Never modifies active XMage or 1.4.61V1 staging.
"""
from __future__ import annotations
import hashlib, json, os, shutil, zipfile
from pathlib import Path

WORKSPACE='migration-workspace'
RUNTIME_REL=Path('mage-client/config/deck-downloader')
ZIP_NAME='XMage_DECK_DOWNLOADER_RUNTIME_BUNDLE.zip'


def sha256(p: Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()


def candidates(root: Path):
    found=[]
    for p in root.rglob('deck-downloader'):
        if p.is_dir() and p.as_posix().lower().endswith('mage-client/config/deck-downloader'):
            found.append(p)
    return found


def main():
    here=Path(__file__).resolve().parent
    ws=here/WORKSPACE
    expanded=ws/'expanded-community'
    if not expanded.exists(): raise RuntimeError(f'Missing community snapshot: {expanded}')
    found=candidates(expanded)
    if not found: raise RuntimeError('RC1 mage-client/config/deck-downloader was not found in expanded-community')
    # Prefer directory with the most files; duplicate snapshot layouts are possible.
    src=max(found,key=lambda p:sum(1 for x in p.rglob('*') if x.is_file()))
    out=ws/'reports'/'migration-analysis'/'deck-downloader-runtime'
    if out.exists(): shutil.rmtree(out)
    bundle=out/'bundle'; runtime=bundle/'mage-client'/'config'/'deck-downloader'
    runtime.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(src,runtime)

    records=[]
    for p in sorted(runtime.rglob('*')):
        if p.is_file():
            records.append({'path':p.relative_to(bundle).as_posix(),'size':p.stat().st_size,'sha256':sha256(p)})
    if not records: raise RuntimeError('Deck Downloader runtime directory is empty')

    required=['deck_library_updater.py']
    names={Path(r['path']).name for r in records}
    missing=[x for x in required if x not in names]
    manifest={'schema':1,'source_snapshot':str(src),'files':records,'required_missing':missing}
    (bundle/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    summary=['XMage Community Patch - DECK DOWNLOADER RUNTIME','================================================','',
             'SAFE MODE: active XMage and 1.4.61V1 staging were not modified.',f'Runtime files: {len(records)}',f'Required missing: {len(missing)}','',
             'FILES']+[f"{r['path']} | {r['size']} bytes | {r['sha256']}" for r in records]
    summary+=['','SAFETY GATE','This bundle is evidence/runtime capture only.','1.4.61V1 remains BLOCKED.']
    (bundle/'RESUMEN_DECK_DOWNLOADER_RUNTIME.txt').write_text('\n'.join(summary)+'\n',encoding='utf-8')

    zip_path=out/ZIP_NAME
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(bundle.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(bundle).as_posix())
    print('=== DECK DOWNLOADER RUNTIME CAPTURE ===')
    print(f'Runtime files: {len(records)}')
    print(f'Required missing: {len(missing)}')
    print(f'ZIP: {zip_path}')
    print(f'ZIP SHA-256: {sha256(zip_path)}')
    print('1.4.61V1 remains BLOCKED. Active XMage was not modified.')
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as e:
        print(f'\nERROR: {e}\nActive XMage was not modified. 1.4.61V1 remains BLOCKED.')
        input('Press Enter to close...'); raise SystemExit(1)
