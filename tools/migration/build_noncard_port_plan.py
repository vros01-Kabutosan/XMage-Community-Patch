#!/usr/bin/env python3
"""Build a surgical port plan from three-way reconstructed source results.

SAFE MODE: reports/patch candidates only. Never modifies active XMage or V1 staging.

Produces:
- NONCARD_PORT_PLAN.txt
- noncard-port-plan.json
- candidate-patches/GameReplay.java.patch (only clean PORT_COMMUNITY_CHANGE)
- review-packages/<source>/ three diffs for REAL_CONFLICT/REVIEW_REQUIRED

No patch is applied automatically.
"""
from __future__ import annotations
import json, shutil
from pathlib import Path

WORKSPACE='migration-workspace'

def load(path: Path):
    if not path.exists(): raise RuntimeError(f'Missing required input: {path}')
    return json.loads(path.read_text(encoding='utf-8'))

def safe_name(s: str)->str:
    return s.replace('/','__').replace('\\','__').replace(':','_')

def main():
    here=Path(__file__).resolve().parent
    root=here/WORKSPACE/'reports'/'migration-analysis'
    src3=load(root/'source-threeway'/'source-threeway.json')
    recon=load(root/'source-reconstruction'/'reconstruction.json')
    recon_root=root/'source-reconstruction'/'selected-noncard-sources'
    diff_root=root/'source-threeway'/'diffs'
    out=root/'port-plan-noncard'
    patches=out/'candidate-patches'; reviews=out/'review-packages'
    if out.exists(): shutil.rmtree(out)
    patches.mkdir(parents=True); reviews.mkdir(parents=True)

    print('=== XMage Community Patch - NON-CARD SURGICAL PORT PLAN ===')
    print('SAFE MODE: no patch is applied.\n')

    rows=src3.get('rows',[])
    counts={}
    for r in rows: counts[r['action']]=counts.get(r['action'],0)+1

    # Copy candidate patch for clean community-only changes.
    clean=[]; review=[]; skip=[]
    for r in rows:
        action=r['action']; source=r['source']; stem=safe_name(source)
        if action=='PORT_COMMUNITY_CHANGE':
            src_diff=diff_root/f'{stem}.V3_to_RC1.diff'
            if not src_diff.exists():
                raise RuntimeError(f'Missing candidate diff for {source}: {src_diff}')
            target=patches/(Path(source).name + '.patch')
            shutil.copy2(src_diff,target)
            clean.append({'source':source,'patch':target.relative_to(out).as_posix()})
        elif action in {'REAL_CONFLICT','REVIEW_REQUIRED'}:
            pkg=reviews/stem; pkg.mkdir(parents=True,exist_ok=True)
            copied=[]
            for suffix in ('V3_to_RC1','V3_to_V1','RC1_to_V1'):
                p=diff_root/f'{stem}.{suffix}.diff'
                if p.exists():
                    t=pkg/p.name; shutil.copy2(p,t); copied.append(t.relative_to(out).as_posix())
            review.append({'action':action,'source':source,'diffs':copied})
        else:
            skip.append({'action':action,'source':source})

    # Priority heuristic: engine/server/ai first, then client UI, then format/version review.
    def priority(item):
        s=item['source'].lower()
        if 'computerplayer.java' in s: return (0,s)
        if '/mage/server/' in s or 'humanplayer.java' in s: return (1,s)
        if '/mage/players/playerimpl.java' in s or '/mage/abilities/' in s or '/mage/game/' in s: return (2,s)
        if 'mageframe.java' in s or 'magebook.java' in s or 'scryfallimagesource.java' in s: return (3,s)
        return (4,s)
    review.sort(key=priority)

    machine={'schema':1,'counts':counts,'clean_port_candidates':clean,'review_required':review,'no_patch_needed':skip}
    (out/'noncard-port-plan.json').write_text(json.dumps(machine,indent=2,ensure_ascii=False),encoding='utf-8')

    lines=['XMage Community Patch - NON-CARD SURGICAL PORT PLAN','==================================================','',
           'SAFE MODE: no patch was applied. Active XMage and 1.4.61V1 staging were not modified.','',
           f"PORT_COMMUNITY_CHANGE candidates: {len(clean)}",f"REAL_CONFLICT/REVIEW_REQUIRED packages: {len(review)}",f"NO PATCH needed (upstream/no-action): {len(skip)}",'',
           'CLEAN PORT CANDIDATES']
    for x in clean: lines.append(f"{x['source']} -> {x['patch']}")
    lines += ['','REVIEW PRIORITY']
    for i,x in enumerate(review,1): lines.append(f"{i:02d}. [{x['action']}] {x['source']}")
    lines += ['','SAFETY GATE','1.4.61V1 remains BLOCKED.','Candidate patches are evidence only until manually verified against official source and compiled/tests pass.']
    (out/'NONCARD_PORT_PLAN.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')

    print(f'Clean port candidates: {len(clean)}')
    print(f'Review packages: {len(review)}')
    print(f'No patch needed: {len(skip)}')
    print(f"Summary: {out/'NONCARD_PORT_PLAN.txt'}")
    print('1.4.61V1 remains BLOCKED. Active XMage was not modified.')
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as e:
        print(f'\nERROR: {e}\nActive XMage was not modified. 1.4.61V1 remains BLOCKED.')
        input('Press Enter to close...'); raise SystemExit(1)
