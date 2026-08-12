#!/usr/bin/env python3
"""XMage Community Patch - batched semantic bytecode analyzer v3.

SAFE BY DESIGN
==============
- NEVER modifies the active XMage installation.
- NEVER copies any 1.4.60 JAR into 1.4.61V1.
- Reads only the isolated migration-workspace produced by the previous tools.
- 1.4.61V1 remains blocked; this tool only produces reports.

WHY v3 IS MUCH FASTER
=====================
The old analyzer launched one Java/javap process per class. mage-sets contains
~44k candidate classes, so process startup dominated runtime. v3 sends classes
to javap in batches, maps the output back to each class, and runs batches in
parallel. V1 is queried only for classes that are semantically different between
official 1.4.60V3 and Community RC1.

Requirements: Python 3 + JDK 17+ with javap.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

WORKSPACE_NAME = "migration-workspace"
ANALYSIS_JSON = "migration-analysis.json"
JAR_VERSION_RE = re.compile(r"-1\.4\.60(?=\.jar$)", re.IGNORECASE)

# 128 class names stays comfortably below the Windows CreateProcess command-line
# limit for normal XMage class names while amortizing JVM startup very heavily.
BATCH_SIZE = 128
JAVAP_TIMEOUT = 180
MAX_BATCH_WORKERS = 12


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
            if not i.is_dir()
            and i.filename.endswith(".class")
            and not i.filename.startswith("META-INF/")
        }


def candidate_classes(record: dict) -> list[str]:
    changed = record.get("changed_classes")
    if isinstance(changed, list):
        return sorted({str(x) for x in changed}, key=str.lower)
    delta = record.get("community_changed_entries", {})
    if isinstance(delta, dict):
        return sorted(
            {str(x) for x in delta if str(x).endswith(".class")},
            key=str.lower,
        )
    return []


def class_name(entry: str) -> str:
    return entry[:-6].replace("/", ".")


def normalize_javap(text: str) -> str:
    """Remove build/debug noise while preserving signatures and instructions."""
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
        # Constant-pool numeric indexes are build details; symbolic comments remain.
        line = re.sub(r"#\d+", "#", line)
        lines.append(line)
    return "\n".join(lines)


def split_javap_blocks(stdout: str, expected: int) -> list[str] | None:
    """Split batched javap output in request order.

    javap normally begins each requested class with 'Compiled from ...'. If an
    unusual class does not produce that marker, caller safely falls back to
    smaller batches instead of guessing/mis-assigning output.
    """
    starts = [m.start() for m in re.finditer(r"(?m)^Compiled from ", stdout)]
    if len(starts) != expected:
        return None
    starts.append(len(stdout))
    return [stdout[starts[i]:starts[i + 1]] for i in range(expected)]


def run_javap_batch_raw(javap: str, jar: Path, entries: list[str]) -> list[str] | None:
    if not entries:
        return []
    cmd = [
        javap, "-c", "-p", "-s", "-classpath", str(jar),
        *[class_name(e) for e in entries],
    ]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=JAVAP_TIMEOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if proc.returncode != 0:
        return None
    return split_javap_blocks(proc.stdout, len(entries))


def javap_hashes_safe(javap: str, jar: Path, entries: list[str]) -> tuple[dict[str, str], list[dict]]:
    """Batched javap with deterministic recursive fallback.

    No class is silently dropped. If a batch cannot be parsed, it is divided in
    half. Only a single-class failure becomes an error entry.
    """
    hashes: dict[str, str] = {}
    errors: list[dict] = []

    def work(batch: list[str]) -> None:
        if not batch:
            return
        try:
            blocks = run_javap_batch_raw(javap, jar, batch)
        except Exception as exc:
            blocks = None
            last_error = str(exc)
        else:
            last_error = "javap batch output could not be parsed"

        if blocks is not None and len(blocks) == len(batch):
            for entry, block in zip(batch, blocks):
                hashes[entry] = sha256_text(normalize_javap(block))
            return

        if len(batch) == 1:
            errors.append({"class": batch[0], "error": last_error})
            return

        mid = len(batch) // 2
        work(batch[:mid])
        work(batch[mid:])

    work(entries)
    return hashes, errors


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def batch_workers() -> int:
    cpu = os.cpu_count() or 4
    # Aggressive on modern CPUs while capping simultaneous JVMs for stability.
    return max(4, min(MAX_BATCH_WORKERS, max(4, cpu // 2)))


def parallel_hash_batches(
    javap: str,
    jar: Path,
    entries: list[str],
    workers: int,
    progress_label: str,
) -> tuple[dict[str, str], list[dict]]:
    """Hash semantic javap output for entries using parallel batched JVMs."""
    if not entries:
        return {}, []

    batches = chunked(entries, BATCH_SIZE)
    all_hashes: dict[str, str] = {}
    all_errors: list[dict] = []
    done_classes = 0
    start = time.time()

    def task(batch: list[str]):
        h, e = javap_hashes_safe(javap, jar, batch)
        return batch, h, e

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, len(batches))) as pool:
        futures = [pool.submit(task, batch) for batch in batches]
        for future in concurrent.futures.as_completed(futures):
            batch, hashes, errors = future.result()
            all_hashes.update(hashes)
            all_errors.extend(errors)
            done_classes += len(batch)
            elapsed = max(time.time() - start, 0.001)
            rate = done_classes / elapsed
            remaining = (len(entries) - done_classes) / rate if rate else 0
            if len(entries) >= 500:
                print(
                    f"    {progress_label}: {done_classes}/{len(entries)} | "
                    f"{rate:.1f} classes/s | ETA ~{remaining/60:.1f} min"
                )

    return all_hashes, all_errors


def analyze_group(
    javap: str,
    v3: Path,
    rc1: Path,
    v1: Path,
    candidates: list[str],
    workers: int,
) -> tuple[list[dict], list[dict], int, list[dict]]:
    entries_v3 = jar_class_entries(v3)
    entries_rc1 = jar_class_entries(rc1)
    entries_v1 = jar_class_entries(v1)

    common = [e for e in candidates if e in entries_v3 and e in entries_rc1]
    added = [e for e in candidates if e not in entries_v3 and e in entries_rc1]
    removed = [e for e in candidates if e in entries_v3 and e not in entries_rc1]
    impossible = [e for e in candidates if e not in entries_v3 and e not in entries_rc1]

    errors: list[dict] = [
        {"class": e, "error": "candidate missing from both V3 and RC1"}
        for e in impossible
    ]

    # Phase A: official V3 vs RC1, both batched.
    v3_hashes, err = parallel_hash_batches(javap, v3, common, workers, "V3")
    errors.extend(err)
    rc1_hashes, err = parallel_hash_batches(javap, rc1, common, workers, "RC1")
    errors.extend(err)

    comparable = [e for e in common if e in v3_hashes and e in rc1_hashes]
    changed_common = [e for e in comparable if v3_hashes[e] != rc1_hashes[e]]
    identical_count = len(comparable) - len(changed_common)

    # Phase B: consult target V1 ONLY for actual semantic changes that still exist.
    target_existing = [e for e in changed_common if e in entries_v1]
    v1_hashes, err = parallel_hash_batches(javap, v1, target_existing, workers, "V1 changed-only")
    errors.extend(err)

    semantic_changes: list[dict] = []
    semantic_conflicts: list[dict] = []

    for entry in changed_common:
        if entry not in v3_hashes or entry not in rc1_hashes:
            continue
        if entry not in entries_v1:
            upstream_status = "REMOVED_UPSTREAM"
            v1_hash = None
        elif entry not in v1_hashes:
            errors.append({"class": entry, "error": "V1 semantic hash unavailable"})
            continue
        else:
            v1_hash = v1_hashes[entry]
            upstream_status = (
                "UPSTREAM_UNCHANGED"
                if v1_hash == v3_hashes[entry]
                else "UPSTREAM_CHANGED"
            )

        record = {
            "class": entry,
            "community_status": "SEMANTICALLY_CHANGED",
            "upstream_status": upstream_status,
            "conflict": upstream_status != "UPSTREAM_UNCHANGED",
            "hashes": {
                "v3": v3_hashes[entry],
                "rc1": rc1_hashes[entry],
                "v1": v1_hash,
            },
        }
        semantic_changes.append(record)
        if record["conflict"]:
            semantic_conflicts.append(record)

    # Community-added classes: safe unless upstream independently added same name.
    for entry in added:
        record = {
            "class": entry,
            "community_status": "ADDED_BY_COMMUNITY",
            "upstream_status": "ADDED_UPSTREAM" if entry in entries_v1 else "UPSTREAM_UNCHANGED",
            "conflict": entry in entries_v1,
            "hashes": {"v3": None, "rc1": None, "v1": None},
        }
        semantic_changes.append(record)
        if record["conflict"]:
            semantic_conflicts.append(record)

    # Community-removed classes: if target still has it, source-level intent must be reviewed.
    for entry in removed:
        record = {
            "class": entry,
            "community_status": "REMOVED_BY_COMMUNITY",
            "upstream_status": "REMOVED_UPSTREAM" if entry not in entries_v1 else "TARGET_STILL_PRESENT",
            "conflict": entry in entries_v1,
            "hashes": {"v3": None, "rc1": None, "v1": None},
        }
        semantic_changes.append(record)
        if record["conflict"]:
            semantic_conflicts.append(record)

    semantic_changes.sort(key=lambda x: x["class"].lower())
    semantic_conflicts.sort(key=lambda x: x["class"].lower())
    errors.sort(key=lambda x: x["class"].lower())
    return semantic_changes, semantic_conflicts, identical_count, errors


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    workspace = script_dir / WORKSPACE_NAME
    migration_dir = workspace / "reports" / "migration-analysis"
    analysis_path = migration_dir / ANALYSIS_JSON

    print("=== XMage Community Patch - BATCHED SEMANTIC BYTECODE ANALYZER v3 ===")
    print("SAFE MODE: active XMage will NOT be modified.\n")

    javap = locate_javap()
    print(f"[OK] javap: {javap}")
    print(f"[INFO] CPU logical threads detected: {os.cpu_count() or 'unknown'}")
    workers = batch_workers()
    print(f"[INFO] Parallel batched javap workers: {workers}")
    print(f"[INFO] Classes per javap batch: {BATCH_SIZE}\n")

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

    groups: dict[tuple[str, str, str], dict] = {}
    global_errors: list[dict] = []

    for rec in records:
        logical = rec["path"]
        v3 = v3_index.get(logical)
        rc1 = rc1_index.get(logical)
        target_logical, v1 = target_candidate(logical, v1_index)
        candidates = candidate_classes(rec)

        if not v3 or not rc1 or not v1:
            global_errors.append({"path": logical, "error": "JAR_NOT_FOUND"})
            continue
        if not candidates:
            global_errors.append({"path": logical, "error": "NO_CLASS_CANDIDATES"})
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

    print(f"[INFO] JAR records: {len(records)}")
    print(f"[INFO] Unique JAR triples: {len(groups)}")
    print(f"[INFO] Duplicate JAR analyses avoided: {max(0, len(records)-len(groups)-len(global_errors))}\n")

    resolved: list[dict] = []
    unique_change_total = 0
    unique_conflict_total = 0
    unique_error_total = 0
    start_all = time.time()

    for idx, group in enumerate(groups.values(), start=1):
        v3: Path = group["v3"]
        rc1: Path = group["rc1"]
        v1: Path = group["v1"]
        candidates = sorted(group["candidates"], key=str.lower)
        labels = ", ".join(logical for logical, _ in group["records"])

        print(f"[{idx}/{len(groups)}] {labels}")
        print(f"  candidate classes: {len(candidates)}")
        group_start = time.time()

        changes, conflicts, identical_count, errors = analyze_group(
            javap, v3, rc1, v1, candidates, workers
        )

        unique_change_total += len(changes)
        unique_conflict_total += len(conflicts)
        unique_error_total += len(errors)

        base_result = {
            "classes_candidates": len(candidates),
            "semantically_identical": identical_count,
            "semantic_changes": changes,
            "semantic_conflicts": conflicts,
            "errors": errors,
            "elapsed_seconds": round(time.time() - group_start, 2),
        }
        for logical, target_logical in group["records"]:
            rec = dict(base_result)
            rec["path"] = logical
            rec["target_path"] = target_logical
            resolved.append(rec)

        print(
            f"  DONE: identical={identical_count}, real_changes={len(changes)}, "
            f"conflicts={len(conflicts)}, errors={len(errors)}, "
            f"time={(time.time()-group_start)/60:.1f} min\n"
        )

    resolved.sort(key=lambda x: x["path"].lower())
    totals = {
        "jar_records": len(records),
        "unique_jar_triples": len(groups),
        "duplicate_jar_analyses_avoided": max(0, len(records)-len(groups)-len(global_errors)),
        "unique_semantic_changes": unique_change_total,
        "unique_semantic_conflicts": unique_conflict_total,
        "unique_javap_errors": unique_error_total,
        "global_errors": len(global_errors),
        "elapsed_seconds": round(time.time() - start_all, 2),
        "batch_workers": workers,
        "batch_size": BATCH_SIZE,
    }

    output = {
        "schema": 3,
        "analyzer": "batched-semantic-bytecode-v3",
        "base": "xmage_1.4.60V3",
        "community": "RC1",
        "target": "xmage_1.4.61V1",
        "jars": resolved,
        "global_errors": global_errors,
        "totals": totals,
    }

    output_dir = migration_dir / "bytecode-analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "semantic-bytecode-analysis.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    summary = [
        "XMage Community Patch - BATCHED SEMANTIC BYTECODE ANALYSIS v3",
        "=============================================================",
        "",
        "SAFE MODE: active XMage was not modified.",
        "javap was executed in class batches instead of one JVM per class.",
        "V1 was analyzed only for genuine V3-vs-RC1 semantic changes.",
        "Duplicate client/server JAR triples were analyzed once.",
        "",
    ]
    for jar in resolved:
        summary.append(
            f"{jar['path']} | candidates={jar['classes_candidates']} | "
            f"identical={jar['semantically_identical']} | "
            f"real_changes={len(jar['semantic_changes'])} | "
            f"conflicts={len(jar['semantic_conflicts'])} | "
            f"errors={len(jar['errors'])} | "
            f"seconds={jar['elapsed_seconds']}"
        )
    summary += [
        "",
        "TOTALS (unique JAR triples; duplicates not double-counted)",
        f"JAR records: {totals['jar_records']}",
        f"Unique JAR triples: {totals['unique_jar_triples']}",
        f"Duplicate analyses avoided: {totals['duplicate_jar_analyses_avoided']}",
        f"Unique semantic changes: {totals['unique_semantic_changes']}",
        f"Unique semantic conflicts with 1.4.61V1: {totals['unique_semantic_conflicts']}",
        f"javap errors: {totals['unique_javap_errors']}",
        f"Global errors: {totals['global_errors']}",
        f"Elapsed seconds: {totals['elapsed_seconds']}",
        f"Parallel batch workers: {totals['batch_workers']}",
        f"Batch size: {totals['batch_size']}",
        "",
        "SAFETY GATE",
        "1.4.61V1 remains BLOCKED. This analyzer performs no migration or activation.",
        "Only the resulting semantic changes are candidates for source-level porting.",
    ]
    (output_dir / "RESUMEN_BYTECODE_SEMANTICO.txt").write_text(
        "\n".join(summary) + "\n", encoding="utf-8"
    )

    print("=== COMPLETE ===")
    print(f"Total elapsed: {totals['elapsed_seconds']/60:.1f} min")
    print(f"Unique semantic changes: {unique_change_total}")
    print(f"Unique conflicts: {unique_conflict_total}")
    print(f"Errors: {unique_error_total + len(global_errors)}")
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
