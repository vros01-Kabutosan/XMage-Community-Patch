#!/usr/bin/env python3
"""Reconstruct RC1 non-card Java source evidence from compiled JARs using CFR.

SAFE MODE:
- reads only migration-workspace
- downloads CFR 0.152 + published SHA-256 from Maven Central
- verifies CFR before execution
- decompiles RC1 JARs into reports/source-reconstruction only
- never modifies active XMage or 1.4.61V1 staging

This is evidence reconstruction, not an automatic source merge.
"""
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, urllib.request
from pathlib import Path

WORKSPACE_NAME='migration-workspace'
CFR_URL='https://repo1.maven.org/maven2/org/benf/cfr/0.152/cfr-0.152.jar'
CFR_SHA_URL=CFR_URL+'.sha256'


def sha256(path: Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()


def download_verified(tool_dir: Path)->Path:
    tool_dir.mkdir(parents=True,exist_ok=True)
    jar=tool_dir/'cfr-0.152.jar'; sf=tool_dir/'cfr-0.152.jar.sha256'
    if not jar.exists(): urllib.request.urlretrieve(CFR_URL,jar)
    if not sf.exists(): urllib.request.urlretrieve(CFR_SHA_URL,sf)
    expected=sf.read_text(encoding='utf-8',errors='replace').strip().split()[0].lower()
    actual=sha256(jar)
    if expected!=actual: raise RuntimeError(f'CFR SHA-256 mismatch: expected {expected}, got {actual}')
    return jar


def file_index(root: Path):
    out={}
    for base,dirs,files in os.walk(root):
        for name in files:
            p=Path(base)/name; rel=p.relative_to(root).as_posix(); parts=rel.split('/'); low=[x.lower() for x in parts]
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


def main():
    here=Path(__file__).resolve().parent
    ws=here/WORKSPACE_NAME
    class_json=ws/'reports'/'migration-analysis'/'bytecode-analysis'/'noncard-classification'/'noncard-source-classification.json'
    if not class_json.exists(): raise RuntimeError('Run RUN_CLASSIFY_NONCARD_WINDOWS.cmd first')
    data=json.loads(class_json.read_text(encoding='utf-8'))
    rc1=merged_rc1_index(ws/'expanded-community')
    out=ws/'reports'/'migration-analysis'/'source-reconstruction'
    decomp=out/'cfr-full-jars'; selected=out/'selected-noncard-sources'; tools=out/'tools'
    if decomp.exists(): shutil.rmtree(decomp)
    if selected.exists(): shutil.rmtree(selected)
    decomp.mkdir(parents=True); selected.mkdir(parents=True)

    print('=== XMage Community Patch - RC1 SOURCE RECONSTRUCTION ===')
    print('SAFE MODE: report/evidence output only.\n')
    cfr=download_verified(tools)
    print(f'[OK] CFR verified: {cfr}')

    # Determine source -> candidate JAR from triage location metadata.
    triage_path=ws/'reports'/'migration-analysis'/'bytecode-analysis'/'conflict-triage'/'conflict-triage.json'
    triage=json.loads(triage_path.read_text(encoding='utf-8'))
    meta={(s.get('probable_source'),s.get('java_entry')):s for s in triage.get('source_files',[]) if s.get('subsystem')!='sets-cards'}
    wanted=[]
    jars=set()
    for row in data.get('sources',[]):
        source=row.get('probable_source',''); java_entry=row.get('java_entry','')
        m=meta.get((source,java_entry),{})
        locations=[x.strip() for x in str(m.get('locations','')).split('|') if x.strip()]
        jar=None
        for loc in locations:
            if loc in rc1: jar=loc; break
        if jar:
            jars.add(jar); wanted.append((source,java_entry,jar,row.get('action','')))

    if not jars: raise RuntimeError('Could not map non-card sources to RC1 JARs')
    print(f'[INFO] Unique RC1 JARs to decompile: {len(jars)}')

    jar_outs={}
    for i,logical in enumerate(sorted(jars),1):
        jar_path=rc1[logical]; dest=decomp/f'{i:02d}_{Path(logical).stem}'
        dest.mkdir(parents=True,exist_ok=True)
        print(f'[{i}/{len(jars)}] CFR {logical}')
        cmd=['java','-jar',str(cfr),str(jar_path),'--outputdir',str(dest),'--silent','true','--comments','false']
        proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',timeout=1200)
        (dest/'cfr.log').write_text(proc.stdout or '',encoding='utf-8')
        if proc.returncode!=0: raise RuntimeError(f'CFR failed for {logical}; see {dest}/cfr.log')
        jar_outs[logical]=dest

    records=[]; missing=[]
    for source,java_entry,logical,action in wanted:
        # CFR path follows package/class path, which matches java_entry for these modules.
        candidate=jar_outs[logical]/java_entry
        if not candidate.exists():
            matches=list(jar_outs[logical].rglob(Path(java_entry).name))
            candidate=matches[0] if len(matches)==1 else candidate
        if candidate.exists():
            target=selected/source
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(candidate,target)
            records.append({'action':action,'source':source,'jar':logical,'reconstructed':target.relative_to(out).as_posix()})
        else:
            missing.append({'action':action,'source':source,'java_entry':java_entry,'jar':logical})

    result={'schema':1,'method':'CFR-0.152-verified','selected_sources':len(records),'missing_sources':len(missing),'records':records,'missing':missing}
    (out/'reconstruction.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    lines=['XMage Community Patch - RC1 SOURCE RECONSTRUCTION','================================================','',
           'CFR 0.152 verified by Maven Central SHA-256.','SAFE MODE: active XMage and 1.4.61V1 staging were not modified.','',
           f'Unique JARs decompiled: {len(jars)}',f'Non-card source files reconstructed: {len(records)}',f'Missing: {len(missing)}','',
           'NEXT GATE: compare reconstructed RC1 evidence with official 1.4.60V3 and 1.4.61V1 source before creating any patch.']
    if missing:
        lines+=['','MISSING']+[f"{x['source']} <- {x['jar']}" for x in missing]
    (out/'RESUMEN_RECONSTRUCCION_RC1.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Non-card sources reconstructed: {len(records)}')
    print(f'Missing: {len(missing)}')
    print(f"Summary: {out/'RESUMEN_RECONSTRUCCION_RC1.txt'}")
    print('1.4.61V1 remains BLOCKED. Active XMage was not modified.')
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as e:
        print(f'\nERROR: {e}\nActive XMage was not modified. 1.4.61V1 remains BLOCKED.')
        input('Press Enter to close...'); raise SystemExit(1)
