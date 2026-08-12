#!/usr/bin/env python3
"""XMage Community Patch - conservative COMMUNITY_DELTA analyzer.

Goal
----
Answer one question safely:
Which RC1 changes are genuinely community changes relative to official
1.4.60V3, and which of those still require action on official 1.4.61V1?

Inputs (read-only):
- migration-analysis.json (three-way analyzer)
- semantic-bytecode-analysis.json (batched semantic analyzer v3)
- conflict-triage.json (source-oriented conflict triage)

Outputs:
- COMMUNITY_DELTA_SUMMARY.txt
- community-delta.json
- COMMUNITY_SOURCE_ACTIONS.csv

Safety principles:
- Never modifies active XMage.
- Never writes into staging.
- Never copies old JARs.
- If evidence is ambiguous, classify as REVIEW_REQUIRED instead of assuming.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

WORKSPACE_NAME = "migration-workspace"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(f"Missing required input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def source_key(module: str, java_entry: str) -> str:
    return f"{module}::{java_entry}"


def classify_source(records: list[dict]) -> tuple[str, str]:
    """Return (action, reason) for one probable source file.

    Conservative ordering:
    1. If any community semantic change collides with upstream -> MERGE_REQUIRED.
    2. If community changed it but upstream stayed identical -> REAPPLY_COMMUNITY_CHANGE.
    3. If the only evidence is upstream-added/changed with no stable community delta -> KEEP_UPSTREAM.
    4. Anything mixed/unclear -> REVIEW_REQUIRED.
    """
    community_statuses = Counter(r.get("community_status", "UNKNOWN") for r in records)
    upstream_statuses = Counter(r.get("upstream_status", "UNKNOWN") for r in records)

    community_changed = sum(
        community_statuses[s]
        for s in ("SEMANTICALLY_CHANGED", "ADDED_BY_COMMUNITY", "REMOVED_BY_COMMUNITY")
    )
    upstream_changed = sum(
        upstream_statuses[s]
        for s in ("UPSTREAM_CHANGED", "ADDED_UPSTREAM", "REMOVED_UPSTREAM", "TARGET_STILL_PRESENT")
    )
    upstream_unchanged = upstream_statuses.get("UPSTREAM_UNCHANGED", 0)

    if community_changed and upstream_changed:
        return (
            "MERGE_REQUIRED",
            "RC1 changed this source and 1.4.61V1 also changed the same semantic area",
        )
    if community_changed and upstream_unchanged and not upstream_changed:
        return (
            "REAPPLY_COMMUNITY_CHANGE",
            "RC1 semantic change is present while upstream target stayed equivalent to 1.4.60V3",
        )
    if not community_changed and upstream_changed:
        return (
            "KEEP_UPSTREAM",
            "No proven community semantic delta; target upstream owns the change",
        )
    return (
        "REVIEW_REQUIRED",
        "Evidence is mixed or insufficient for automatic classification",
    )


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    migration_root = script_dir / WORKSPACE_NAME / "reports" / "migration-analysis"
    three_way_path = migration_root / "migration-analysis.json"
    bytecode_path = migration_root / "bytecode-analysis" / "semantic-bytecode-analysis.json"
    triage_path = migration_root / "bytecode-analysis" / "conflict-triage" / "conflict-triage.json"

    out_dir = migration_root / "community-delta"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== XMage Community Patch - COMMUNITY_DELTA ===")
    print("SAFE MODE: analysis only; active XMage is not modified.\n")

    three_way = load_json(three_way_path)
    bytecode = load_json(bytecode_path)
    triage = load_json(triage_path)

    # Build source-oriented semantic evidence from v3 results.
    source_evidence: dict[str, list[dict]] = defaultdict(list)
    source_meta: dict[str, dict] = {}

    triage_sources = triage.get("source_files", [])
    for src in triage_sources:
        key = source_key(src.get("module", ""), src.get("java_entry", ""))
        source_meta[key] = src

    for jar in bytecode.get("jars", []):
        module = None
        jar_path = jar.get("path", "")
        # Map jar record to triage module by matching location when possible.
        candidates = [
            s for s in triage_sources
            if jar_path and jar_path in str(s.get("locations", ""))
        ]
        module_by_entry = {
            s.get("java_entry"): s.get("module", "") for s in candidates
        }

        for rec in jar.get("semantic_changes", []):
            cls = rec.get("class", "")
            if not cls.endswith(".class"):
                continue
            java_entry = cls[:-6].split("$", 1)[0] + ".java"
            mod = module_by_entry.get(java_entry)
            if not mod:
                # fallback: locate same java_entry uniquely in triage
                matches = [s for s in triage_sources if s.get("java_entry") == java_entry]
                if len(matches) == 1:
                    mod = matches[0].get("module", "")
                else:
                    mod = "unknown"
            key = source_key(mod, java_entry)
            source_evidence[key].append(rec)
            if key not in source_meta:
                source_meta[key] = {
                    "module": mod,
                    "java_entry": java_entry,
                    "probable_source": java_entry,
                    "subsystem": "unknown",
                    "locations": jar_path,
                }

    action_rows = []
    for key, records in source_evidence.items():
        meta = source_meta.get(key, {})
        action, reason = classify_source(records)
        community_counts = Counter(r.get("community_status", "UNKNOWN") for r in records)
        upstream_counts = Counter(r.get("upstream_status", "UNKNOWN") for r in records)
        action_rows.append({
            "action": action,
            "subsystem": meta.get("subsystem", "unknown"),
            "module": meta.get("module", "unknown"),
            "probable_source": meta.get("probable_source", meta.get("java_entry", "")),
            "semantic_records": len(records),
            "community_statuses": "; ".join(f"{k}:{v}" for k, v in sorted(community_counts.items())),
            "upstream_statuses": "; ".join(f"{k}:{v}" for k, v in sorted(upstream_counts.items())),
            "reason": reason,
        })

    # Add proven community-only overlays from three-way analysis.
    safe_overlays = []
    review_community_files = []
    for rec in three_way.get("community_only", []):
        status = rec.get("status", "")
        path = rec.get("path", "")
        if status == "SAFE_COMMUNITY_OVERLAY":
            safe_overlays.append(path)
        else:
            review_community_files.append({"path": path, "status": status})

    action_order = {
        "MERGE_REQUIRED": 0,
        "REAPPLY_COMMUNITY_CHANGE": 1,
        "REVIEW_REQUIRED": 2,
        "KEEP_UPSTREAM": 3,
    }
    action_rows.sort(
        key=lambda r: (
            action_order.get(r["action"], 9),
            r["subsystem"],
            r["probable_source"].lower(),
        )
    )

    with (out_dir / "COMMUNITY_SOURCE_ACTIONS.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = [
            "action", "subsystem", "module", "probable_source", "semantic_records",
            "community_statuses", "upstream_statuses", "reason",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(action_rows)

    action_counts = Counter(r["action"] for r in action_rows)
    subsystem_counts = Counter()
    for r in action_rows:
        if r["action"] != "KEEP_UPSTREAM":
            subsystem_counts[r["subsystem"]] += 1

    machine = {
        "schema": 1,
        "base": "xmage_1.4.60V3",
        "community": "RC1",
        "target": "xmage_1.4.61V1",
        "action_counts": dict(action_counts),
        "non_upstream_source_files": sum(v for k, v in action_counts.items() if k != "KEEP_UPSTREAM"),
        "safe_community_overlays": sorted(safe_overlays),
        "community_files_requiring_review": review_community_files,
        "source_actions": action_rows,
    }
    (out_dir / "community-delta.json").write_text(
        json.dumps(machine, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    summary = [
        "XMage Community Patch - COMMUNITY_DELTA",
        "=======================================",
        "",
        "Official 1.4.60V3 -> Community RC1 -> Official 1.4.61V1",
        "SAFE MODE: no XMage files were modified.",
        "",
        "SOURCE ACTION COUNTS",
    ]
    for action in ("MERGE_REQUIRED", "REAPPLY_COMMUNITY_CHANGE", "REVIEW_REQUIRED", "KEEP_UPSTREAM"):
        summary.append(f"{action}: {action_counts.get(action, 0)}")

    summary += [
        "",
        f"Source files that are NOT simply KEEP_UPSTREAM: {machine['non_upstream_source_files']}",
        f"Safe community overlays: {len(safe_overlays)}",
        f"Community-only files requiring review: {len(review_community_files)}",
        "",
        "NON-UPSTREAM SOURCE FILES BY SUBSYSTEM",
    ]
    for name, count in subsystem_counts.most_common():
        summary.append(f"{name}: {count}")

    summary += ["", "SAFE COMMUNITY OVERLAYS"]
    for path in sorted(safe_overlays):
        summary.append(path)

    summary += ["", "TOP 100 ACTIONS"]
    for row in action_rows[:100]:
        summary.append(
            f"[{row['action']}] [{row['subsystem']}] {row['probable_source']} | "
            f"community={row['community_statuses']} | upstream={row['upstream_statuses']}"
        )

    summary += [
        "",
        "SAFETY GATE",
        "Do NOT activate 1.4.61V1 yet.",
        "KEEP_UPSTREAM items should not receive RC1 code automatically.",
        "REAPPLY_COMMUNITY_CHANGE items are candidates for clean source reapplication.",
        "MERGE_REQUIRED and REVIEW_REQUIRED items require explicit source-level review.",
    ]

    (out_dir / "COMMUNITY_DELTA_SUMMARY.txt").write_text(
        "\n".join(summary) + "\n", encoding="utf-8"
    )

    print("Community delta complete.")
    for action in ("MERGE_REQUIRED", "REAPPLY_COMMUNITY_CHANGE", "REVIEW_REQUIRED", "KEEP_UPSTREAM"):
        print(f"{action}: {action_counts.get(action, 0)}")
    print(f"Safe overlays: {len(safe_overlays)}")
    print(f"Summary: {out_dir / 'COMMUNITY_DELTA_SUMMARY.txt'}")
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
