#!/usr/bin/env python3
"""Semantic bytecode analyzer for XMage Community Patch migration.

Purpose
-------
The previous three-way analyzer compares raw .class hashes. That is intentionally
conservative, but separate Java builds can produce different class bytes even
when source behavior is unchanged. This tool uses `javap` disassembly to reduce
that noise and identify classes whose executable bytecode/signatures really
changed between:

  official 1.4.60V3 -> Community RC1 -> official 1.4.61V1

It NEVER modifies the active XMage installation and NEVER copies old JARs into
1.4.61V1.

Requirements: Python 3 + a JDK providing `javap` on PATH.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

WORKSPACE_NAME = "migration-workspace"
ANALYSIS_JSON = "migration-analysis.json"
JAR_VERSION_RE = re.compile(r"-1\.4\.60(?=\.jar$)", re.IGNORECASE)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
        "javap was not found. Install/use a JDK (not only a JRE) and ensure JAVA_HOME/bin or javap is on PATH."
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


def class_entries(jar: Path) -> set[str]:
    with zipfile.ZipFile(jar) as zf:
        return {
            i.filename for i in zf.infolist()
            if not i.is_dir() and i.filename.endswith(".class") and not i.filename.startswith("META-INF/")
        }


def extract_class(jar: Path, entry: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(jar) as zf:
        dest.write_bytes(zf.read(entry))
    return dest


def normalize_javap(text: str) -> str:
    """Keep API/signatures/instructions, discard location/build-only noise."""
    lines = []
    skip_prefixes = (
        "Compiled from ",
        "Classfile ",
        "Last modified ",
        "  SHA-256 checksum ",
        "  minor version:",
        "  major version:",
    )
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(p.strip()) for p in skip_prefixes):
            continue
        if stripped.startswith("LineNumberTable:") or stripped.startswith("LocalVariableTable:"):
            continue
        # javap -c -p -s should not emit constant-pool indexes as semantic data,
        # but instruction comments can contain generated pool ids. Remove leading #NN references.
        line = re.sub(r"#\d+", "#", line)
        lines.append(line)
    return "\n".join(lines)


def javap_semantic_hash(javap: str, class_file: Path) -> tuple[str, str]:
    proc = subprocess.run(
        [javap, "-c", "-p", "-s", str(class_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"javap failed for {class_file.name}: {proc.stderr.strip()}")
    normalized = normalize_javap(proc.stdout)
    return sha256_bytes(normalized.encode("utf-8")), normalized


def compare_class(javap: str, jars: tuple[Path, Path, Path], entry: str, temp: Path) -> dict:
    labels = ("v3", "rc1", "v1")
    hashes = {}
    texts = {}
    exists = {}
    for label, jar in zip(labels, jars):
        with zipfile.ZipFile(jar) as zf:
            if entry not in zf.namelist():
                exists[label] = False
                hashes[label] = None
                texts[label] = None
                continue
        exists[label] = True
        class_path = temp / label / entry
        extract_class(jar, entry, class_path)
        h, txt = javap_semantic_hash(javap, class_path)
        hashes[label] = h
        texts[label] = txt

    v3, rc1, v1 = hashes["v3"], hashes["rc1"], hashes["v1"]
    if not exists["v3"] and exists["rc1"]:
        community_status = "ADDED_BY_COMMUNITY"
    elif exists["v3"] and not exists["rc1"]:
        community_status = "REMOVED_BY_COMMUNITY"
    elif v3 == rc1:
        community_status = "SEMANTICALLY_IDENTICAL"
    else:
        community_status = "SEMANTICALLY_CHANGED"

    if not exists["v3"] and exists["v1"]:
        upstream_status = "ADDED_UPSTREAM"
    elif exists["v3"] and not exists["v1"]:
        upstream_status = "REMOVED_UPSTREAM"
    elif v3 == v1:
        upstream_status = "UPSTREAM_UNCHANGED"
    else:
        upstream_status = "UPSTREAM_CHANGED"

    conflict = community_status in {"SEMANTICALLY_CHANGED", "ADDED_BY_COMMUNITY", "REMOVED_BY_COMMUNITY"} and upstream_status != "UPSTREAM_UNCHANGED"
    return {
        "class": entry,
        "community_status": community_status,
        "upstream_status": upstream_status,
        "conflict": conflict,
        "hashes": hashes,
    }


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    workspace = script_dir / WORKSPACE_NAME
    reports = workspace / "reports"
    migration_dir = reports / "migration-analysis"
    analysis_path = migration_dir / ANALYSIS_JSON

    print("=== XMage Community Patch - SEMANTIC BYTECODE ANALYZER ===")
    print("SAFE MODE: active XMage will NOT be modified.\n")

    javap = locate_javap()
    print(f"[OK] javap: {javap}")

    if not analysis_path.exists():
        raise RuntimeError("Run RUN_ANALYZE_MIGRATION_WINDOWS.cmd first")

    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    v3_index = file_index(workspace / "extracted" / "upstream-v3")
    rc1_index = merged_rc1_index(workspace / "expanded-community")
    v1_index = file_index(workspace / "staging" / "xmage_1.4.61V1-clean")

    jar_records = [
        r for r in analysis.get("modified", [])
        if r.get("path", "").lower().endswith(".jar")
    ]

    out = {
        "schema": 1,
        "base": "xmage_1.4.60V3",
        "community": "RC1",
        "target": "xmage_1.4.61V1",
        "jars": [],
    }
    summary = [
        "XMage Community Patch - SEMANTIC BYTECODE ANALYSIS",
        "===================================================",
        "",
        "Raw class hashes were filtered through javap disassembly.",
        "This reduces false positives caused by separate Java builds.",
        "",
    ]

    with tempfile.TemporaryDirectory(prefix="xmage-bytecode-") as tmp_name:
        tmp = Path(tmp_name)
        for idx, rec in enumerate(jar_records, start=1):
            logical = rec["path"]
            v3 = v3_index.get(logical)
            rc1 = rc1_index.get(logical)
            target_logical, v1 = target_candidate(logical, v1_index)
            if not v3 or not rc1 or not v1:
                out["jars"].append({"path": logical, "status": "JAR_NOT_FOUND"})
                summary.append(f"[JAR_NOT_FOUND] {logical}")
                continue

            print(f"[{idx}/{len(jar_records)}] {logical}")
            entries = sorted(class_entries(v3) | class_entries(rc1) | class_entries(v1), key=str.lower)
            semantic_changes = []
            semantic_conflicts = []
            errors = []

            for n, entry in enumerate(entries, start=1):
                try:
                    result = compare_class(javap, (v3, rc1, v1), entry, tmp / str(idx))
                except Exception as exc:
                    errors.append({"class": entry, "error": str(exc)})
                    continue
                if result["community_status"] != "SEMANTICALLY_IDENTICAL":
                    semantic_changes.append(result)
                    if result["conflict"]:
                        semantic_conflicts.append(result)
                if n % 500 == 0:
                    print(f"  {n}/{len(entries)} classes")

            jar_result = {
                "path": logical,
                "target_path": target_logical,
                "classes_scanned": len(entries),
                "semantic_changes": semantic_changes,
                "semantic_conflicts": semantic_conflicts,
                "errors": errors,
            }
            out["jars"].append(jar_result)
            summary.append(
                f"{logical} | scanned={len(entries)} | real_changes={len(semantic_changes)} | "
                f"real_conflicts={len(semantic_conflicts)} | errors={len(errors)}"
            )

    totals = {
        "jars": len(out["jars"]),
        "semantic_changes": sum(len(x.get("semantic_changes", [])) for x in out["jars"]),
        "semantic_conflicts": sum(len(x.get("semantic_conflicts", [])) for x in out["jars"]),
        "errors": sum(len(x.get("errors", [])) for x in out["jars"]),
    }
    out["totals"] = totals

    output_dir = migration_dir / "bytecode-analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "semantic-bytecode-analysis.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    summary += [
        "",
        "TOTALS",
        f"JARs analyzed: {totals['jars']}",
        f"Semantically changed classes: {totals['semantic_changes']}",
        f"Semantic conflicts with 1.4.61V1: {totals['semantic_conflicts']}",
        f"javap errors: {totals['errors']}",
        "",
        "NEXT:",
        "Only the semantically changed classes should be reconstructed/ported at source level.",
        "1.4.61V1 remains blocked until those changes compile and pass tests.",
    ]
    (output_dir / "RESUMEN_BYTECODE_SEMANTICO.txt").write_text(
        "\n".join(summary) + "\n", encoding="utf-8"
    )

    print("\nDone.")
    print(f"Summary: {output_dir / 'RESUMEN_BYTECODE_SEMANTICO.txt'}")
    print(f"JSON:    {output_dir / 'semantic-bytecode-analysis.json'}")
    print("Active XMage was not modified. 1.4.61V1 remains BLOCKED.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled. Active XMage was not modified.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("Active XMage was not modified.")
        input("Press Enter to close...")
        raise SystemExit(1)
