#!/usr/bin/env python3
"""Extract Community Deck Downloader Java sources and audit dependencies.

Purpose
-------
The non-card review isolated MageFrame's Deck Downloader integration as the only
proven community-specific non-card behavior that still needs porting. This tool
reconstructs the entire RC1 `mage/client/decks` package, checks which classes are
absent/present in official V3 and V1 JARs, scans source-level imports/references,
and packages the result into one ZIP for source-level porting.

SAFE MODE:
- reads migration-workspace only
- reuses verified CFR 0.152
- writes reports/evidence only
- never modifies active XMage
- never modifies 1.4.61V1 staging
"""
from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess, zipfile
from pathlib import Path

WORKSPACE='migration-workspace'
PACKAGE_PREFIX='mage/client/decks/'
BUNDLE='XMage_DECK_DOWNLOADER_SOURCE_BUNDLE.zip'


def load(path: Path):
    if not path.exists(): raise RuntimeError(f'Missing required input: {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def sha256(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()


def file_index(root: Path):
    out={}
    for base,dirs,files in os.walk(root):
        dirs.sort(key=str.lower); files.sort(key=str.lower)
        for name in files:
            p=Path(base)/name
            if name=='.extracted-ok': continue
            rel=p.relative_to(root).as_posix(); parts=rel.split('/'); low=[x.lower() for x in parts]
            for anchor in ('mage-client','mage-server'):
                if anchor in low:
                    i=low.index(anchor); out['/'.join(parts[i:])]=p; break
    return out


def merged_rc1_index(expanded: Path):
    out={}
    for anchor in ('mage-client','mage-server'):
        for d in expanded.rglob(anchor):
            if d.is_dir(): out.update(file_index(d.parent))
    return out


def jar_entries(jar: Path):
    with zipfile.ZipFile(jar) as z:
        return {i.filename for i in z.infolist() if not i.is_dir()}


def decompile(cfr: Path, jar: Path, dest: Path):
    if dest.exists(): shutil.rmtree(dest)
    dest.mkdir(parents=True)
    p=subprocess.run(['java','-jar',str(cfr),str(jar),'--outputdir',str(dest),'--silent','true','--comments','false'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',timeout=1200)
    (dest/'cfr.log').write_text(p.stdout or '',encoding='utf-8')
    if p.returncode!=0: raise RuntimeError(f'CFR failed for {jar}')


def main():
    here=Path(__file__).resolve().parent
    ws=here/WORKSPACE
    recon=ws/'reports'/'migration-analysis'/'source-reconstruction'
    cfr=recon/'tools'/'cfr-0.152.jar'
    if not cfr.exists(): raise RuntimeError('Verified CFR missing; run source reconstruction first')

    rc1_idx=merged_rc1_index(ws/'expanded-community')
    v3_idx=file_index(ws/'extracted'/'upstream-v3')
    v1_idx=file_index(ws/'staging'/'xmage_1.4.61V1-clean')
    logical='mage-client/lib/mage-client-1.4.60.jar'
    rc1=rc1_idx.get(logical); v3=v3_idx.get(logical)
    v1=v1_idx.get('mage-client/lib/mage-client-1.4.61.jar') or next((p for k,p in v1_idx.items() if k.endswith('/mage-client-1.4.61.jar')),None)
    if not rc1 or not v3 or not v1: raise RuntimeError('Could not locate client JAR triple')

    print('=== XMage Community Patch - DECK DOWNLOADER SOURCE AUDIT ===')
    print('SAFE MODE: evidence only.\n')

    rc1_entries=jar_entries(rc1); v3_entries=jar_entries(v3); v1_entries=jar_entries(v1)
    package_classes=sorted(e for e in rc1_entries if e.startswith(PACKAGE_PREFIX) and e.endswith('.class') and '$' not in Path(e).name)
    if not package_classes: raise RuntimeError('No RC1 mage/client/decks top-level classes found')

    out=ws/'reports'/'migration-analysis'/'deck-downloader-source'
    if out.exists(): shutil.rmtree(out)
    work=out/'decompiled-rc1-client'; bundle=out/'bundle'; src_out=bundle/'sources'
    decompile(cfr,rc1,work)
    src_out.mkdir(parents=True)

    records=[]; refs=set(); missing=[]
    for cls in package_classes:
        java=cls[:-6]+'.java'; src=work/java
        if not src.exists():
            missing.append(java); continue
        dst=src_out/java; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
        text=src.read_text(encoding='utf-8',errors='replace')
        # Collect direct imports plus fully-qualified mage references.
        for m in re.finditer(r'^import\s+([\w.]+);',text,re.M): refs.add(m.group(1))
        for m in re.finditer(r'\bmage\.[A-Za-z0-9_$.]+',text): refs.add(m.group(0).rstrip('.'))
        records.append({
            'class':cls,
            'java':java,
            'present_v3':cls in v3_entries,
            'present_v1':cls in v1_entries,
            'sha256':sha256(dst),
        })

    # Community package refs that may also be additions outside mage/client/decks.
    dependency_candidates=[]
    for ref in sorted(refs):
        entry=ref.replace('.','/')+'.class'
        if entry in rc1_entries and entry not in v3_entries:
            dependency_candidates.append({'reference':ref,'class':entry,'present_v1':entry in v1_entries})

    manifest={
        'schema':1,
        'package':PACKAGE_PREFIX,
        'top_level_classes':records,
        'missing_sources':missing,
        'community_dependency_candidates':dependency_candidates,
        'client_jar_sha256':{'v3':sha256(v3),'rc1':sha256(rc1),'v1':sha256(v1)},
    }
    (bundle/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')

    lines=['XMage Community Patch - DECK DOWNLOADER SOURCE AUDIT','===================================================','',
           'SAFE MODE: active XMage and 1.4.61V1 staging were not modified.','',
           f'RC1 top-level mage/client/decks classes: {len(records)}',
           f'Missing reconstructed sources: {len(missing)}',
           f'Community dependency candidates outside package: {len(dependency_candidates)}','',
           'PACKAGE CLASSES']
    for r in records:
        state='COMMUNITY_ONLY' if not r['present_v3'] and not r['present_v1'] else ('NOW_UPSTREAM' if r['present_v1'] and not r['present_v3'] else 'EXISTING')
        lines.append(f"[{state}] {r['java']}")
    if dependency_candidates:
        lines += ['','DEPENDENCY CANDIDATES']
        for d in dependency_candidates: lines.append(f"{d['reference']} | present_v1={d['present_v1']}")
    lines += ['','NEXT GATE','Do not patch MageFrame until every community-only Deck Downloader source/dependency is captured and source-reviewed.','1.4.61V1 remains BLOCKED.']
    (bundle/'RESUMEN_DECK_DOWNLOADER_SOURCE.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')

    zip_path=out/BUNDLE
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(bundle.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(bundle).as_posix())
    print(f'Package classes: {len(records)}')
    print(f'Missing: {len(missing)}')
    print(f'Community dependency candidates: {len(dependency_candidates)}')
    print(f'ZIP: {zip_path}')
    print('1.4.61V1 remains BLOCKED. Active XMage was not modified.')
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as e:
        print(f'\nERROR: {e}\nActive XMage was not modified. 1.4.61V1 remains BLOCKED.')
        input('Press Enter to close...'); raise SystemExit(1)
