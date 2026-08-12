#!/usr/bin/env python3
"""XMage Community Patch - conflict triage for semantic migration results.

Reads only:
  migration-workspace/reports/migration-analysis/bytecode-analysis/
    semantic-bytecode-analysis.json

Produces compact, source-oriented reports by:
- deduplicating duplicate client/server JAR records;
- collapsing inner classes (Foo$1.class, Foo$Bar.class) to Foo.java;
- grouping conflicts by subsystem/module/package;
- generating probable upstream Java source paths;
- ranking source files by conflict density.

SAFE MODE: never modifies XMage, never activates 1.4.61V1, never writes into
staging. Reports only.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

WORKSPACE_NAME = "migration-workspace"

MODULE_ROOTS = {
    "mage": "Mage/src/main/java",
    "mage-client": "Mage.Client/src/main/java",
    "mage-common": "Mage.Common/src/main/java",
    "mage-deck-constructed": "Mage.Plugins/Mage.Deck/src/main/java",
    "mage-sets": "Mage.Sets/src/main/java",
    "mage-player-ai": "Mage.Server.Plugins/Mage.Player.AI/src/main/java",
    "mage-server": "Mage.Server/src/main/java",
    "mage-player-human": "Mage.Server.Plugins/Mage.Player.Human/src/main/java",
    "mage-counter-plugin": "Mage.Client/src/main/java",
}


def outer_class_entry(entry: str) -> str:
    if not entry.endswith(".class"):
        return entry
    stem = entry[:-6]
    stem = stem.split("$", 1)[0]
    return stem + ".java"


def package_of(java_path: str) -> str:
    p = Path(java_path).parent.as_posix()
    return p if p != "." else "<root>"


def subsystem(java_path: str, jar_path: str) -> str:
    low = java_path.lower()
    jar = jar_path.lower()
    if "mage/cards/" in low or "mage/sets/" in low or "mage-sets" in jar:
        return "sets-cards"
    if "player-ai" in jar or "/ai/" in low or "mage/player/ai" in low:
        return "ai"
    if "mage-client" in jar or "client/" in low or "gui/" in low:
        return "client"
    if "mage-server" in jar or "server/" in low:
        return "server"
    if "/plugins/" in jar:
        return "plugins"
    return "engine"


def jar_module(jar_path: str) -> str:
    name = Path(jar_path).name
    name = re.sub(r"-1\.4\.\d+.*(?=\.jar$)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"-0\.\d+.*(?=\.jar$)", "", name, flags=re.IGNORECASE)
    return name[:-4] if name.lower().endswith(".jar") else name


def probable_source(module: str, java_entry: str) -> str:
    root = MODULE_ROOTS.get(module)
    if root:
        return f"{root}/{java_entry}"
    return java_entry


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    analysis_dir = script_dir / WORKSPACE_NAME / "reports" / "migration-analysis" / "bytecode-analysis"
    src = analysis_dir / "semantic-bytecode-analysis.json"
    out_dir = analysis_dir / "conflict-triage"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== XMage Community Patch - CONFLICT TRIAGE ===")
    print("SAFE MODE: reports only; active XMage is not modified.\n")

    if not src.exists():
        raise RuntimeError(f"Missing {src}. Run the semantic bytecode analyzer first.")

    data = json.loads(src.read_text(encoding="utf-8"))
    if data.get("schema") not in (2, 3):
        raise RuntimeError("Unsupported semantic analysis schema. Run analyzer v3 first.")

    unique_conflicts: dict[tuple[str, str], dict] = {}
    source_records: dict[tuple[str, str], dict] = {}
    jar_seen = set()

    for jar in data.get("jars", []):
        jar_path = jar.get("path", "")
        module = jar_module(jar_path)
        # The same binary JAR may be listed for client + server. Conflict identity
        # is module + class, so duplicate locations collapse naturally.
        for conflict in jar.get("semantic_conflicts", []):
            cls = conflict.get("class")
            if not cls:
                continue
            key = (module, cls)
            rec = unique_conflicts.setdefault(
                key,
                {
                    "module": module,
                    "class": cls,
                    "locations": set(),
                    "community_status": conflict.get("community_status", ""),
                    "upstream_status": conflict.get("upstream_status", ""),
                },
            )
            rec["locations"].add(jar_path)

            java_entry = outer_class_entry(cls)
            source_key = (module, java_entry)
            source = source_records.setdefault(
                source_key,
                {
                    "module": module,
                    "java_entry": java_entry,
                    "probable_source": probable_source(module, java_entry),
                    "subsystem": subsystem(java_entry, jar_path),
                    "classes": set(),
                    "locations": set(),
                    "upstream_statuses": Counter(),
                    "community_statuses": Counter(),
                },
            )
            source["classes"].add(cls)
            source["locations"].add(jar_path)
            source["upstream_statuses"][conflict.get("upstream_status", "UNKNOWN")] += 1
            source["community_statuses"][conflict.get("community_status", "UNKNOWN")] += 1

    conflict_rows = []
    for rec in unique_conflicts.values():
        conflict_rows.append({
            "module": rec["module"],
            "class": rec["class"],
            "java_entry": outer_class_entry(rec["class"]),
            "community_status": rec["community_status"],
            "upstream_status": rec["upstream_status"],
            "locations": " | ".join(sorted(rec["locations"])),
        })
    conflict_rows.sort(key=lambda r: (r["module"].lower(), r["java_entry"].lower(), r["class"].lower()))

    source_rows = []
    for rec in source_records.values():
        source_rows.append({
            "subsystem": rec["subsystem"],
            "module": rec["module"],
            "probable_source": rec["probable_source"],
            "java_entry": rec["java_entry"],
            "conflicting_classes": len(rec["classes"]),
            "upstream_statuses": "; ".join(f"{k}:{v}" for k, v in sorted(rec["upstream_statuses"].items())),
            "community_statuses": "; ".join(f"{k}:{v}" for k, v in sorted(rec["community_statuses"].items())),
            "locations": " | ".join(sorted(rec["locations"])),
        })
    source_rows.sort(key=lambda r: (-int(r["conflicting_classes"]), r["subsystem"], r["probable_source"].lower()))

    with (out_dir / "UNIQUE_CLASS_CONFLICTS.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(conflict_rows[0].keys()) if conflict_rows else ["module"])
        writer.writeheader()
        writer.writerows(conflict_rows)

    with (out_dir / "SOURCE_FILES_TO_PORT.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(source_rows[0].keys()) if source_rows else ["module"])
        writer.writeheader()
        writer.writerows(source_rows)

    subsystem_counts = Counter(r["subsystem"] for r in source_rows)
    module_counts = Counter(r["module"] for r in source_rows)

    summary = [
        "XMage Community Patch - CONFLICT TRIAGE",
        "========================================",
        "",
        "Input: semantic-bytecode-analysis.json (analyzer v3)",
        "SAFE MODE: no XMage files were modified.",
        "",
        f"Unique conflicting classes: {len(conflict_rows)}",
        f"Probable Java source files to review/port: {len(source_rows)}",
        "",
        "SOURCE FILES BY SUBSYSTEM",
    ]
    for name, count in subsystem_counts.most_common():
        summary.append(f"{name}: {count}")

    summary += ["", "SOURCE FILES BY MODULE"]
    for name, count in module_counts.most_common():
        summary.append(f"{name}: {count}")

    summary += ["", "TOP 100 SOURCE FILES BY CONFLICT DENSITY"]
    for row in source_rows[:100]:
        summary.append(
            f"[{row['subsystem']}] {row['probable_source']} | "
            f"conflicting_classes={row['conflicting_classes']} | {row['upstream_statuses']}"
        )

    summary += [
        "",
        "NEXT GATE",
        "Do not activate 1.4.61V1 yet.",
        "Port and compile source files in priority order, then run regression tests.",
    ]

    (out_dir / "RESUMEN_CONFLICTOS.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")

    machine = {
        "schema": 1,
        "unique_conflicting_classes": len(conflict_rows),
        "probable_source_files": len(source_rows),
        "subsystem_counts": dict(subsystem_counts),
        "module_counts": dict(module_counts),
        "source_files": source_rows,
    }
    (out_dir / "conflict-triage.json").write_text(
        json.dumps(machine, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Unique conflicting classes: {len(conflict_rows)}")
    print(f"Probable Java source files: {len(source_rows)}")
    print(f"Summary: {out_dir / 'RESUMEN_CONFLICTOS.txt'}")
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
