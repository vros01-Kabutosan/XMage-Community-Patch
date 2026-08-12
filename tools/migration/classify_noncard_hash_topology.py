#!/usr/bin/env python3
"""XMage Community Patch - strict non-card three-way semantic classifier.

Uses analyzer v3 semantic hashes already present in:
  migration-workspace/reports/migration-analysis/bytecode-analysis/
    semantic-bytecode-analysis.json
and the source-oriented triage:
  .../conflict-triage/conflict-triage.json

Only NON-CARD source files are classified.

Class-level topology rules:
- RC1 == V1 != V3  -> UPSTREAM_ALREADY_HAS
- V3 == V1 != RC1  -> PORT_COMMUNITY_CHANGE
- all three differ -> REAL_CONFLICT
- V3 == RC1        -> NO_ACTION
- missing/ambiguous hashes -> REVIEW_REQUIRED

Source-level policy is conservative:
- any REAL_CONFLICT -> REAL_CONFLICT
- else any REVIEW_REQUIRED -> REVIEW_REQUIRED
- else any PORT_COMMUNITY_CHANGE + any UPSTREAM_ALREADY_HAS -> REVIEW_REQUIRED
- else any PORT_COMMUNITY_CHANGE -> PORT_COMMUNITY_CHANGE
- else all UPSTREAM_ALREADY_HAS/NO_ACTION -> UPSTREAM_ALREADY_HAS or NO_ACTION

SAFE MODE: reports only. Never modifies active XMage or 1.4.61V1 staging.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

WORKSPACE_NAME = "migration-workspace"


def load(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(f"Missing required input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def outer_java(entry: str) -> str:
    if not entry.endswith(".class"):
        return entry
    return entry[:-6].split("$", 1)[0] + ".java"


def classify_hashes(h: dict, community_status: str, upstream_status: str) -> str:
    v3, rc1, v1 = h.get("v3"), h.get("rc1"), h.get("v1")

    # Handle structural add/remove cases first.
    if community_status == "ADDED_BY_COMMUNITY":
        if upstream_status == "ADDED_UPSTREAM":
            # Same named class exists independently upstream; without comparable
            # base hash this must be reviewed.
            return "REVIEW_REQUIRED"
        return "PORT_COMMUNITY_CHANGE"
    if community_status == "REMOVED_BY_COMMUNITY":
        if upstream_status == "REMOVED_UPSTREAM":
            return "UPSTREAM_ALREADY_HAS"
        return "REAL_CONFLICT"

    if v3 is None or rc1 is None:
        return "REVIEW_REQUIRED"

    if v3 == rc1:
        return "NO_ACTION"

    if v1 is None:
        # Target removed or semantic hash unavailable while RC1 changed it.
        return "REAL_CONFLICT" if upstream_status in {"REMOVED_UPSTREAM", "UPSTREAM_CHANGED"} else "REVIEW_REQUIRED"

    if rc1 == v1 and rc1 != v3:
        return "UPSTREAM_ALREADY_HAS"
    if v3 == v1 and rc1 != v3:
        return "PORT_COMMUNITY_CHANGE"
    if len({v3, rc1, v1}) == 3:
        return "REAL_CONFLICT"
    return "REVIEW_REQUIRED"


def collapse_source(actions: list[str]) -> str:
    s = set(actions)
    if "REAL_CONFLICT" in s:
        return "REAL_CONFLICT"
    if "REVIEW_REQUIRED" in s:
        return "REVIEW_REQUIRED"
    if "PORT_COMMUNITY_CHANGE" in s and "UPSTREAM_ALREADY_HAS" in s:
        return "REVIEW_REQUIRED"
    if "PORT_COMMUNITY_CHANGE" in s:
        return "PORT_COMMUNITY_CHANGE"
    if "UPSTREAM_ALREADY_HAS" in s:
        return "UPSTREAM_ALREADY_HAS"
    return "NO_ACTION"


def main() -> int:
    here = Path(__file__).resolve().parent
    root = here / WORKSPACE_NAME / "reports" / "migration-analysis" / "bytecode-analysis"
    sem = load(root / "semantic-bytecode-analysis.json")
    triage = load(root / "conflict-triage" / "conflict-triage.json")

    out = root / "noncard-classification"
    out.mkdir(parents=True, exist_ok=True)

    print("=== XMage Community Patch - NON-CARD HASH TOPOLOGY CLASSIFIER ===")
    print("SAFE MODE: reports only; active XMage is not modified.\n")

    # Build metadata lookup only for non-card triaged sources.
    meta = {}
    for src in triage.get("source_files", []):
        if src.get("subsystem") == "sets-cards":
            continue
        key = (src.get("module", ""), src.get("java_entry", ""))
        meta[key] = src

    # For each semantic class record, map it into one of the known non-card sources.
    evidence = defaultdict(list)
    unmatched = []

    for jar in sem.get("jars", []):
        jar_path = jar.get("path", "")
        # Candidate module/source matches by location from triage metadata.
        location_sources = [
            (k, src) for k, src in meta.items()
            if jar_path and jar_path in str(src.get("locations", ""))
        ]
        by_java = defaultdict(list)
        for k, src in location_sources:
            by_java[src.get("java_entry", "")].append(k)

        for rec in jar.get("semantic_changes", []):
            cls = rec.get("class", "")
            if not cls.endswith(".class"):
                continue
            java_entry = outer_java(cls)
            keys = by_java.get(java_entry, [])
            if not keys:
                # Fallback to globally unique non-card java_entry.
                keys = [k for k, src in meta.items() if src.get("java_entry") == java_entry]
            if len(keys) != 1:
                continue
            key = keys[0]
            action = classify_hashes(
                rec.get("hashes", {}),
                rec.get("community_status", ""),
                rec.get("upstream_status", ""),
            )
            evidence[key].append({
                "class": cls,
                "action": action,
                "community_status": rec.get("community_status", ""),
                "upstream_status": rec.get("upstream_status", ""),
                "hashes": rec.get("hashes", {}),
            })

    source_rows = []
    for key, src in meta.items():
        ev = evidence.get(key, [])
        actions = [e["action"] for e in ev]
        source_action = collapse_source(actions) if actions else "REVIEW_REQUIRED"
        counts = Counter(actions)
        source_rows.append({
            "action": source_action,
            "subsystem": src.get("subsystem", "unknown"),
            "module": src.get("module", "unknown"),
            "probable_source": src.get("probable_source", src.get("java_entry", "")),
            "java_entry": src.get("java_entry", ""),
            "classes_with_hash_evidence": len(ev),
            "class_actions": "; ".join(f"{k}:{v}" for k, v in sorted(counts.items())),
            "conflicting_classes_from_triage": src.get("conflicting_classes", 0),
        })

    order = {
        "REAL_CONFLICT": 0,
        "PORT_COMMUNITY_CHANGE": 1,
        "REVIEW_REQUIRED": 2,
        "UPSTREAM_ALREADY_HAS": 3,
        "NO_ACTION": 4,
    }
    source_rows.sort(key=lambda r: (order.get(r["action"], 9), r["subsystem"], r["probable_source"].lower()))

    fields = ["action", "subsystem", "module", "probable_source", "java_entry", "classes_with_hash_evidence", "class_actions", "conflicting_classes_from_triage"]
    with (out / "NONCARD_SOURCE_CLASSIFICATION.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(source_rows)

    counts = Counter(r["action"] for r in source_rows)
    by_sub = defaultdict(Counter)
    for r in source_rows:
        by_sub[r["subsystem"]][r["action"]] += 1

    machine = {
        "schema": 1,
        "method": "strict-three-way-semantic-hash-topology",
        "counts": dict(counts),
        "by_subsystem": {k: dict(v) for k, v in by_sub.items()},
        "sources": source_rows,
    }
    (out / "noncard-source-classification.json").write_text(json.dumps(machine, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "XMage Community Patch - NON-CARD SOURCE CLASSIFICATION",
        "======================================================",
        "",
        "Method: strict three-way semantic hash topology (V3 / RC1 / V1)",
        "SAFE MODE: no XMage files were modified.",
        "",
        "SOURCE COUNTS",
    ]
    for a in ("REAL_CONFLICT", "PORT_COMMUNITY_CHANGE", "REVIEW_REQUIRED", "UPSTREAM_ALREADY_HAS", "NO_ACTION"):
        lines.append(f"{a}: {counts.get(a, 0)}")
    lines += ["", "BY SUBSYSTEM"]
    for sub in sorted(by_sub):
        parts = ", ".join(f"{a}={n}" for a, n in sorted(by_sub[sub].items()))
        lines.append(f"{sub}: {parts}")
    lines += ["", "ACTION LIST"]
    for r in source_rows:
        lines.append(f"[{r['action']}] [{r['subsystem']}] {r['probable_source']} | evidence_classes={r['classes_with_hash_evidence']} | {r['class_actions']}")
    lines += [
        "",
        "SAFETY GATE",
        "1.4.61V1 remains BLOCKED.",
        "UPSTREAM_ALREADY_HAS/NO_ACTION must not receive RC1 code.",
        "PORT_COMMUNITY_CHANGE are candidates for clean source reapplication.",
        "REAL_CONFLICT/REVIEW_REQUIRED require explicit source-level merge review.",
    ]
    (out / "RESUMEN_NONCARD_CLASIFICACION.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    for a in ("REAL_CONFLICT", "PORT_COMMUNITY_CHANGE", "REVIEW_REQUIRED", "UPSTREAM_ALREADY_HAS", "NO_ACTION"):
        print(f"{a}: {counts.get(a, 0)}")
    print(f"Summary: {out/'RESUMEN_NONCARD_CLASIFICACION.txt'}")
    print("1.4.61V1 remains BLOCKED. Active XMage was not modified.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("Active XMage was not modified. 1.4.61V1 remains BLOCKED.")
        input("Press Enter to close...")
        raise SystemExit(1)
