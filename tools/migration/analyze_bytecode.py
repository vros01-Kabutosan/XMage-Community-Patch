#!/usr/bin/env python3
"""Fast semantic bytecode analyzer for XMage Community Patch migration.

This replaces the original exhaustive analyzer. It is designed to remain safe:
- NEVER modifies the active XMage installation.
- NEVER copies old 1.4.60 JARs into 1.4.61V1.
- Reads only the isolated migration workspace.
- Uses the previous three-way analysis as its candidate list.

Speed strategy:
1. Analyze only classes already flagged as changed by the raw three-way audit.
2. Deduplicate identical V3/RC1/V1 JAR triples so client/server copies are not
   analyzed twice.
3. Compare V3 vs RC1 first. V1 is disassembled only if RC1 is semantically
   different from V3.
4. Run javap jobs in parallel with a conservative worker limit.

Requirements: Python 3 + a JDK providing javap.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import zipfile
from pathlib import Path

WORKSPACE_NAME = "migration-workspace"
ANALYSIS_JSON = "migration-analysis.json"
JAR_VERSION_RE = re.compile(r"-1\.4\.60(?=\.jar$)", re.IGNORECASE)
DEFAULT_MAX_WORKERS = 12
JAVAP_TIMEOUT = 30


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def locate_javap() -> str:
    tool = shutil.which("javap")
    if tool:
        return tool
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / ("javap.exe" if os.name == "nt" else "javap")
        if candidate.exists():
            return str(candidate)
    raise RuntimeError(
        "javap was not found. A JDK is required. Ensure JAVA_HOME/bin or javap is on PATH."
    )


def file_index(root: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for base, dirs, files in os.walk(root):
        dirs.sort(key=str.lower)
        files.sort(key=str.lower)
        for name in files:
            p = Path(base) / name
            if name == ".extracted-ok":
                continue
            rel = p.relative_to(root).as_posix()
            parts = rel.split("/")
            low = [x.lower() for x in parts]
            logical = None
            for anchor in ("mage-client", "mage-server"):
                if anchor in low:
                    i = low.index(anchor)
                    logical = "/".join(parts[i:])
                    break
            if logical:
                out[logical] = p
    return out


def merged_rc1_index(expanded: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for anchor in ("mage-client", "mage-server"):
        for d in expanded.rglob(anchor):
            if d.is_dir():
                out.update(file_index(d.parent))
    return out


def target_candidate(logical_v3: str, v1_index: dict[str, Path]) -> tuple[str | None, Path | None]:
    if logical_v3 in v1_index:
        return logical_v3, v1_index[logical_v3]
    upgraded = JAR_VERSION_RE.sub("-1.4.61", logical_v3)
    if upgraded in v1_index:
        return upgraded, v1_index[upgraded]
    basename = Path(upgraded).name.lower()
    matches = [(k, v) for k, v in v1_index.items() if Path(k).name.lower() == basename]
    if len(matches) == 1:
        return matches[0]
    return None, None


def jar_class_entries(jar: Path) -> set[str]:
    with zipfile.ZipFile(jar) as zf:
        return {
            i.filename for i in zf.infolist()
            if not i.is_dir() and i.filename.endswith(".class") and not i.filename.startswith("META-INF/")
        }


def normalize_javap(text: str) -> str:
    lines = []
    skip_prefixes = (
        "Compiled from ",
        "Classfile ",
        "Last modified ",
        "SHA-256 checksum ",
        "minor version:",
        "major version:",
    )
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(p) for p in skip_prefixes):
            continue
        if stripped.startswith("LineNumberTable:") or stripped.startswith("LocalVariableTable:"):
            continue
        line = re.sub(r"#\d+", "#", line)
        lines.append(line)
    return "\n".join(lines)


def class_name_from_entry(entry: str) -> str:
    return entry[:-6].replace("/", ".")


def javap_hash(javap: str, jar: Path, entry: str) -> str:
    class_name = class_name_from_entry(entry)
    proc = subprocess.run(
        [javap, "-c", "-p", "-s", "-classpath", str(jar), class_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=JAVAP_TIMEOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"javap failed: {class_name}")
    return sha256_text(normalize_javap(proc.stdout))


def analyze_one_class(
    javap: str,
    v3: Path,
    rc1: Path,
    v1: Path,
    entry: str,
    entries_v3: set[str],
    entries_rc1: set[str],
    entries_v1: set[str],
) -> dict:
    exists_v3 = entry in entries_v3
    exists_rc1 = entry in entries_rc1
    exists_v1 = entry in entries_v1

    hashes = {"v3": None, "rc1": None, "v1": None}

    if not exists_v3 and exists_rc1:
        community_status = "ADDED_BY_COMMUNITY"
        hashes["rc1"] = javap_hash(javap, rc1, entry)
    elif exists_v3 and not exists_rc1:
        community_status = "REMOVED_BY_COMMUNITY"
        hashes["v3"] = javap_hash(javap, v3, entry)
    elif exists_v3 and exists_rc1:
        hashes["v3"] = javap_hash(javap, v3, entry)
        hashes["rc1"] = javap_hash(javap, rc1, entry)
        if hashes["v3"] == hashes["rc1"]:
            return {
                "class": entry,
                "community_status": "SEMANTICALLY_IDENTICAL",
                "upstream_status": "NOT_NEEDED",
                "conflict": False,
                "hashes": hashes,
            }
        community_status = "SEMANTICALLY_CHANGED"
    else:
        return {
            "class": entry,
            "community_status": "MISSING_FROM_BOTH_BASE_AND_RC1",
            "upstream_status": "NOT_NEEDED",
            "conflict": False,
            "hashes": hashes,
        }

    # Only reach V1 when RC1 actually changed behavior/signature vs V3.
    if exists_v1:
        hashes["v1"] = javap_hash(javap, v1, entry)

    if not exists_v3 and exists_v1:
        upstream_status = "ADDED_UPSTREAM"
    elif exists_v3 and not exists_v1:
        upstream_status = "REMOVED_UPSTREAM"
    elif exists_v3 and exists_v1:
        if hashes["v3"] is None:
            hashes["v3"] = javap_hash(javap, v3, entry)
        upstream_status = "UPSTREAM_UNCHANGED" if hashes["v3"] == hashes["v1"] else "UPSTREAM_CHANGED"
    else:
        upstream_status = "UPSTREAM_UNCHANGED"

    conflict = upstream_status != "UPSTREAM_UNCHANGED"
    return {
        "class": entry,
        "community_status": community_status,
        "upstream_status": upstream_status,
        "conflict": conflict,
        "hashes": hashes,
    }


def candidate_classes(record: dict) -> list[str]:
    changed = record.get("changed_classes")
    if isinstance(changed, list):
        return sorted(set(str(x) for x in changed), key=str.lower)
    delta = record.get("community_changed_entries", {})
    if isinstance(delta, dict):
        return sorted(
            {str(x) for x in delta if str(x).endswith(".class")},
            key=str.lower,
        )
    return []


def workers_count() -> int:
    cpu = os.cpu_count() or 4
    # Conservative: enough parallelism to remove process-start bottleneck without
    # consuming every logical CPU or making the desktop unusable.
    return max(4, min(DEFAULT_MAX_WORKERS, max(4, cpu // 2)))


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    workspace = script_dir / WORKSPACE_NAME
    migration_dir = workspace / "reports" / "migration-analysis"
    analysis_path = migration_dir / ANALYSIS_JSON

    print("=== XMage Community Patch - FAST SEMANTIC BYTECODE ANALYZER v2 ===")
    print("SAFE MODE: active XMage will NOT be modified.\n")

    javap = locate_javap()
    print(f"[OK] javap: {javap}")

    if not analysis_path.exists():
        raise RuntimeError("Run RUN_ANALYZE_MIGRATION_WINDOWS.cmd first")

    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    v3_index = file_index(workspace / "extracted" / "upstream-v3")
    rc1_index = merged_rc1_index(workspace / "expanded-community")
    v1_index = file_index(workspace / "staging" / "xmage_1.4.61V1-clean")

    records = [
        r for r in analysis.get("modified", [])
        if r.get("path", "").lower().endswith(".jar")
    ]

    resolved = []
    errors_global = []
    groups: dict[tuple[str, str, str], dict] = {}

    print(f"[INFO] JAR records from previous analysis: {len(records)}")

    for rec in records:
        logical = rec["path"]
        v3 = v3_index.get(logical)
        rc1 = rc1_index.get(logical)
        target_logical, v1 = target_candidate(logical, v1_index)
        if not v3 or not rc1 or not v1:
            errors_global.append({"path": logical, "error": "JAR_NOT_FOUND"})
            continue

        candidates = candidate_classes(rec)
        if not candidates:
            errors_global.append({"path": logical, "error": "NO_CLASS_CANDIDATES"})
            continue

        key = (sha256_file(v3), sha256_file(rc1), sha256_file(v1))
        group = groups.setdefault(
            key,
            {
                "v3": v3,
                "rc1": rc1,
                "v1": v1,
                "records": [],
                "candidates": set(),
            },
        )
        group["records"].append((logical, target_logical))
        group["candidates"].update(candidates)

    print(f"[INFO] Unique JAR triples after deduplication: {len(groups)}")
    duplicate_savings = len(records) - len(groups) - len(errors_global)
    if duplicate_savings > 0:
        print(f"[INFO] Duplicate JAR analyses avoided: {duplicate_savings}")

    max_workers = workers_count()
    print(f"[INFO] Parallel javap workers: {max_workers}")
    print("[INFO] Only classes flagged by the previous audit will be examined.\n")

    start_all = time.time()

    for group_idx, group in enumerate(groups.values(), start=1):
        v3: Path = group["v3"]
        rc1: Path = group["rc1"]
        v1: Path = group["v1"]
        candidates = sorted(group["candidates"], key=str.lower)
        labels = ", ".join(x[0] for x in group["records"])

        print(f"[{group_idx}/{len(groups)}] {labels}")
        print(f"  candidate classes: {len(candidates)}")

        entries_v3 = jar_class_entries(v3)
        entries_rc1 = jar_class_entries(rc1)
        entries_v1 = jar_class_entries(v1)

        semantic_changes = []
        semantic_conflicts = []
        class_errors = []
        identical_count = 0
        completed = 0
        lock = threading.Lock()
        group_start = time.time()

        def task(entry: str):
            return analyze_one_class(
                javap, v3, rc1, v1, entry,
                entries_v3, entries_rc1, entries_v1,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(task, entry): entry for entry in candidates}
            try:
                for future in concurrent.futures.as_completed(futures):
                    entry = futures[future]
                    try:
                        result = future.result()
                        if result["community_status"] == "SEMANTICALLY_IDENTICAL":
                            identical_count += 1
                        elif result["community_status"] != "MISSING_FROM_BOTH_BASE_AND_RC1":
                            semantic_changes.append(result)
                            if result["conflict"]:
                                semantic_conflicts.append(result)
                    except Exception as exc:
                        class_errors.append({"class": entry, "error": str(exc)})

                    completed += 1
                    if completed % 250 == 0 or completed == len(candidates):
                        elapsed = max(time.time() - group_start, 0.001)
                        rate = completed / elapsed
                        remaining = (len(candidates) - completed) / rate if rate else 0
                        print(
                            f"  {completed}/{len(candidates)} | "
                            f"{rate:.1f} classes/s | ETA ~{remaining/60:.1f} min"
                        )
            except KeyboardInterrupt:
                for f in futures:
                    f.cancel()
                raise

        semantic_changes.sort(key=lambda x: x["class"].lower())
        semantic_conflicts.sort(key=lambda x: x["class"].lower())
        class_errors.sort(key=lambda x: x["class"].lower())

        base_result = {
            "classes_candidates": len(candidates),
            "semantically_identical": identical_count,
            "semantic_changes": semantic_changes,
            "semantic_conflicts": semantic_conflicts,
            "errors": class_errors,
        }

        for logical, target_logical in group["records"]:
            record_result = dict(base_result)
            record_result["path"] = logical
            record_result["target_path"] = target_logical
            resolved.append(record_result)

        print(
            f"  DONE: real_changes={len(semantic_changes)}, "
            f"conflicts={len(semantic_conflicts)}, errors={len(class_errors)}\n"
        )

    resolved.sort(key=lambda x: x.get("path", "").lower())
    totals = {
        "jar_records": len(records),
        "unique_jar_triples": len(groups),
        "duplicate_jar_analyses_avoided": max(0, duplicate_savings),
        "semantic_changes": sum(len(x.get("semantic_changes", [])) for x in resolved),
        "semantic_conflicts": sum(len(x.get("semantic_conflicts", [])) for x in resolved),
        "javap_errors": sum(len(x.get("errors", [])) for x in resolved),
        "global_errors": len(errors_global),
        "elapsed_seconds": round(time.time() - start_all, 2),
        "workers": max_workers,
    }

    out = {
        "schema": 2,
        "analyzer": "fast-semantic-bytecode-v2",
        "base": "xmage_1.4.60V3",
        "community": "RC1",
        "target": "xmage_1.4.61V1",
        "jars": resolved,
        "global_errors": errors_global,
        "totals": totals,
    }

    output_dir = migration_dir / "bytecode-analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "semantic-bytecode-analysis.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    summary = [
        "XMage Community Patch - FAST SEMANTIC BYTECODE ANALYSIS v2",
        "==========================================================",
        "",
        "SAFE MODE: active XMage was not modified.",
        "Only candidate classes from the three-way audit were examined.",
        "Duplicate client/server JAR triples were analyzed once and reused.",
        "V1 javap was skipped whenever RC1 was semantically identical to V3.",
        "",
    ]
    for jar in resolved:
        summary.append(
            f"{jar['path']} | candidates={jar['classes_candidates']} | "
            f"identical={jar['semantically_identical']} | "
            f"real_changes={len(jar['semantic_changes'])} | "
            f"conflicts={len(jar['semantic_conflicts'])} | "
            f"errors={len(jar['errors'])}"
        )
    summary += [
        "",
        "TOTALS",
        f"JAR records: {totals['jar_records']}",
        f"Unique JAR triples: {totals['unique_jar_triples']}",
        f"Duplicate analyses avoided: {totals['duplicate_jar_analyses_avoided']}",
        f"Semantic changes: {totals['semantic_changes']}",
        f"Semantic conflicts with 1.4.61V1: {totals['semantic_conflicts']}",
        f"javap errors: {totals['javap_errors']}",
        f"Global errors: {totals['global_errors']}",
        f"Elapsed seconds: {totals['elapsed_seconds']}",
        f"Parallel workers: {totals['workers']}",
        "",
        "SAFETY GATE",
        "1.4.61V1 remains BLOCKED. No migration/activation is performed by this analyzer.",
        "Only semantically changed classes will be considered for source-level porting.",
    ]
    (output_dir / "RESUMEN_BYTECODE_SEMANTICO.txt").write_text(
        "\n".join(summary) + "\n", encoding="utf-8"
    )

    print("=== COMPLETE ===")
    print(f"Elapsed: {totals['elapsed_seconds']/60:.1f} min")
    print(f"Semantic changes: {totals['semantic_changes']}")
    print(f"Conflicts: {totals['semantic_conflicts']}")
    print(f"Errors: {totals['javap_errors'] + totals['global_errors']}")
    print(f"Summary: {output_dir / 'RESUMEN_BYTECODE_SEMANTICO.txt'}")
    print("Active XMage was not modified. 1.4.61V1 remains BLOCKED.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled safely. Active XMage was not modified.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("Active XMage was not modified. 1.4.61V1 remains BLOCKED.")
        input("Press Enter to close...")
        raise SystemExit(1)
