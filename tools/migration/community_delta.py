#!/usr/bin/env python3
"""XMage Community Patch - COMMUNITY_DELTA v2.

Conservative source migration planner. It deliberately does NOT infer ownership
from every bytecode difference: different builds can produce huge false deltas.
Only source candidates already proven by the three-way conflict/triage stage are
considered. Everything else belongs to upstream unless independently proven.

SAFE MODE: reports only. Never modifies active XMage or staging.
"""
from __future__ import annotations
import csv, json
from collections import Counter
from pathlib import Path

WORKSPACE_NAME = "migration-workspace"

def load(path: Path):
    if not path.exists(): raise RuntimeError(f"Missing required input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    here=Path(__file__).resolve().parent
    root=here/WORKSPACE_NAME/"reports"/"migration-analysis"
    triage=load(root/"bytecode-analysis"/"conflict-triage"/"conflict-triage.json")
    three=load(root/"migration-analysis.json")
    out=root/"community-delta"; out.mkdir(parents=True,exist_ok=True)
    print("=== XMage Community Patch - COMMUNITY_DELTA v2 ===")
    print("SAFE MODE: proven three-way conflicts only.\n")

    rows=[]
    for s in triage.get("source_files",[]):
        up=str(s.get("upstream_statuses",""))
        com=str(s.get("community_statuses",""))
        # Triage contains only classes where RC1 and target differ materially.
        # We cannot safely decide ownership from compiler bytecode alone, so every
        # such source is a source-level merge/review candidate, never auto-copied.
        action="MERGE_REVIEW"
        rows.append({
            "action":action,
            "subsystem":s.get("subsystem","unknown"),
            "module":s.get("module","unknown"),
            "probable_source":s.get("probable_source",s.get("java_entry","")),
            "conflicting_classes":s.get("conflicting_classes",0),
            "community_statuses":com,
            "upstream_statuses":up,
        })

    overlays=[]; overlay_review=[]
    for r in three.get("community_only",[]):
        p=r.get("path",""); st=r.get("status","")
        if st=="SAFE_COMMUNITY_OVERLAY": overlays.append(p)
        else: overlay_review.append({"path":p,"status":st})

    rows.sort(key=lambda r:(r["subsystem"],-int(r["conflicting_classes"]),r["probable_source"].lower()))
    fields=["action","subsystem","module","probable_source","conflicting_classes","community_statuses","upstream_statuses"]
    with (out/"COMMUNITY_SOURCE_ACTIONS.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

    subs=Counter(r["subsystem"] for r in rows)
    machine={"schema":2,"method":"proven-three-way-conflicts-only","merge_review_sources":len(rows),
             "safe_community_overlays":sorted(set(overlays)),"community_overlay_review":overlay_review,
             "subsystems":dict(subs),"source_actions":rows}
    (out/"community-delta.json").write_text(json.dumps(machine,indent=2,ensure_ascii=False),encoding="utf-8")

    lines=["XMage Community Patch - COMMUNITY_DELTA v2","==========================================","",
           "Official 1.4.60V3 -> Community RC1 -> Official 1.4.61V1",
           "SAFE MODE: no XMage files were modified.","",
           "IMPORTANT: v1 bytecode-wide ownership inference was rejected as false-positive prone.",
           "This report uses only the already-proven three-way conflict set.","",
           f"MERGE/REVIEW SOURCE FILES: {len(rows)}",f"SAFE COMMUNITY OVERLAYS: {len(set(overlays))}",
           f"COMMUNITY OVERLAYS REQUIRING REVIEW: {len(overlay_review)}","","BY SUBSYSTEM"]
    for k,v in subs.most_common(): lines.append(f"{k}: {v}")
    lines += ["","SAFE COMMUNITY OVERLAYS"] + sorted(set(overlays))
    lines += ["","PRIORITY NON-CARD SOURCES"]
    noncards=[r for r in rows if r["subsystem"]!="sets-cards"]
    noncards.sort(key=lambda r:-int(r["conflicting_classes"]))
    for r in noncards:
        lines.append(f"[{r['subsystem']}] {r['probable_source']} | conflicting_classes={r['conflicting_classes']}")
    lines += ["","SAFETY GATE","1.4.61V1 remains BLOCKED.",
              "Do not copy RC1 JARs over 1.4.61V1.",
              "Next: resolve non-card source changes against upstream source, then handle sets/cards in bulk."]
    (out/"COMMUNITY_DELTA_SUMMARY.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"MERGE/REVIEW source files: {len(rows)}")
    print(f"Safe overlays: {len(set(overlays))}")
    print(f"Summary: {out/'COMMUNITY_DELTA_SUMMARY.txt'}")
    print("1.4.61V1 remains BLOCKED. Active XMage was not modified.")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as e:
        print(f"\nERROR: {e}\nActive XMage was not modified. 1.4.61V1 remains BLOCKED.")
        input("Press Enter to close..."); raise SystemExit(1)
