#!/usr/bin/env python3
"""Three-way migration analyzer for XMage Community Patch.

Uses the workspace prepared by audit_and_stage.py and compares:
  official 1.4.60V3 -> Community RC1 -> official 1.4.61V1

It never modifies the active XMage installation and never copies old 1.4.60
JARs into 1.4.61. For modified JARs it compares ZIP/JAR entries to identify
exact classes/resources changed by RC1 and whether upstream changed the same
entries in 1.4.61V1.

Python 3 standard library only.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

WORKSPACE_NAME = "migration-workspace"
TEXT_EXTS = {".txt", ".xml", ".properties", ".md", ".cmd", ".bat", ".sh", ".py"}
IGNORE_JAR_PREFIXES = ("META-INF/",)
VERSION_RE = re.compile(r"-1\.4\.60(?=\.jar$)", re.IGNORECASE)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
            if logical is None and parts[-1] in {
                "installed.properties", "run-launcher-and-wait.cmd",
                "run-LAUNCHER.cmd", "XMageLauncher-0.3.8.jar",
            }:
                logical = parts[-1]
            if logical:
                out[logical] = p
    return out


def find_rc1_roots(expanded: Path) -> list[Path]:
    roots = []
    for candidate in expanded.rglob("mage-client"):
        if candidate.is_dir():
            roots.append(candidate.parent)
    for candidate in expanded.rglob("mage-server"):
        if candidate.is_dir():
            roots.append(candidate.parent)
    # unique while preserving order
    seen = set()
    result = []
    for r in roots:
        key = str(r.resolve())
        if key not in seen:
            seen.add(key)
            result.append(r)
    return result


def merged_rc1_index(expanded: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for root in find_rc1_roots(expanded):
        out.update(file_index(root))
    return out


def read_audit(report: Path) -> dict:
    data = json.loads(report.read_text(encoding="utf-8"))
    if data.get("schema") not in (2, 3):
        raise RuntimeError("Run audit_and_stage.py v2.1 or newer first")
    return data


def find_official_root(workspace: Path, which: str) -> Path:
    if which == "v3":
        base = workspace / "extracted" / "upstream-v3"
    elif which == "v1":
        base = workspace / "staging" / "xmage_1.4.61V1-clean"
    else:
        raise ValueError(which)
    if not base.exists():
        raise RuntimeError(f"Missing prepared workspace: {base}")
    return base


def jar_entries(path: Path) -> dict[str, str]:
    result = {}
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir() or info.filename.startswith(IGNORE_JAR_PREFIXES):
                continue
            h = hashlib.sha256(zf.read(info.filename)).hexdigest()
            result[info.filename] = h
    return result


def delta(base: dict[str, str], other: dict[str, str]) -> dict[str, str]:
    d = {}
    for name in sorted(set(base) | set(other), key=str.lower):
        a = base.get(name)
        b = other.get(name)
        if a is None:
            d[name] = "ADDED"
        elif b is None:
            d[name] = "DELETED"
        elif a != b:
            d[name] = "MODIFIED"
    return d


def v1_candidate(logical_v3: str, v1_index: dict[str, Path]) -> tuple[str | None, Path | None]:
    if logical_v3 in v1_index:
        return logical_v3, v1_index[logical_v3]
    upgraded = VERSION_RE.sub("-1.4.61", logical_v3)
    if upgraded in v1_index:
        return upgraded, v1_index[upgraded]
    basename = Path(upgraded).name.lower()
    matches = [(k, v) for k, v in v1_index.items() if Path(k).name.lower() == basename]
    if len(matches) == 1:
        return matches[0]
    return None, None


def text_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)


def write_text_diff(out: Path, a: Path, b: Path, a_label: str, b_label: str) -> None:
    diff = difflib.unified_diff(
        text_lines(a), text_lines(b), fromfile=a_label, tofile=b_label, n=4
    )
    out.write_text("".join(diff), encoding="utf-8")


def same_hash_elsewhere(path: Path, official: dict[str, Path]) -> list[str]:
    h = sha256_file(path)
    return [logical for logical, p in official.items() if p.stat().st_size == path.stat().st_size and sha256_file(p) == h]


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    workspace = script_dir / WORKSPACE_NAME
    reports = workspace / "reports"
    audit_path = reports / "rc1-vs-upstream-v3.json"
    expanded = workspace / "expanded-community"

    print("=== XMage Community Patch - THREE-WAY MIGRATION ANALYZER ===")
    print("SAFE MODE: no active XMage files are modified.\n")

    if not audit_path.exists():
        raise RuntimeError("Missing audit report. Run RUN_AUDIT_WINDOWS.cmd first.")

    audit = read_audit(audit_path)
    v3_index = file_index(find_official_root(workspace, "v3"))
    v1_index = file_index(find_official_root(workspace, "v1"))
    rc1_index = merged_rc1_index(expanded)

    if not rc1_index:
        raise RuntimeError("Could not index expanded RC1 Client/Server payload")

    analysis_dir = reports / "migration-analysis"
    if analysis_dir.exists():
        shutil.rmtree(analysis_dir)
    (analysis_dir / "jar-details").mkdir(parents=True)
    (analysis_dir / "text-diffs").mkdir(parents=True)

    items = audit.get("attention", [])
    modified = [x for x in items if x.get("status") == "MODIFIED"]
    community_only = [x for x in items if x.get("status") == "COMMUNITY_ONLY"]

    result = {
        "schema": 1,
        "base": "xmage_1.4.60V3",
        "community": "RC1",
        "target": "xmage_1.4.61V1",
        "modified": [],
        "community_only": [],
    }

    summary = [
        "XMage Community Patch - THREE-WAY MIGRATION ANALYSIS",
        "=====================================================",
        "",
        "Official 1.4.60V3 -> Community RC1 -> Official 1.4.61V1",
        "No old JAR is copied into 1.4.61V1 by this tool.",
        "",
    ]

    for item in modified:
        logical = item["path"]
        rc1 = rc1_index.get(logical)
        v3 = v3_index.get(logical)
        target_logical, v1 = v1_candidate(logical, v1_index)
        record = {"path": logical, "target_path": target_logical}

        if rc1 is None or v3 is None:
            record["status"] = "INDEX_ERROR"
            result["modified"].append(record)
            continue

        if logical.lower().endswith(".jar"):
            if v1 is None:
                record["status"] = "TARGET_JAR_NOT_FOUND"
                result["modified"].append(record)
                summary.append(f"[TARGET_JAR_NOT_FOUND] {logical}")
                continue

            base_entries = jar_entries(v3)
            rc1_entries = jar_entries(rc1)
            v1_entries = jar_entries(v1)
            community_delta = delta(base_entries, rc1_entries)
            upstream_delta = delta(base_entries, v1_entries)
            conflicts = sorted(set(community_delta) & set(upstream_delta), key=str.lower)

            changed_classes = sorted(
                [x for x in community_delta if x.endswith(".class")], key=str.lower
            )
            changed_resources = sorted(
                [x for x in community_delta if not x.endswith(".class")], key=str.lower
            )

            status = "JAR_SOURCE_RECONSTRUCTION_REQUIRED"
            if conflicts:
                status = "JAR_CONFLICT_WITH_1.4.61V1"

            record.update({
                "status": status,
                "community_changed_entries": community_delta,
                "upstream_changed_entries": upstream_delta,
                "conflicts": conflicts,
                "changed_classes": changed_classes,
                "changed_resources": changed_resources,
            })

            detail_name = logical.replace("/", "__").replace("\\", "__") + ".json"
            (analysis_dir / "jar-details" / detail_name).write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            summary.append(
                f"[{status}] {logical} | RC1 entries={len(community_delta)} | "
                f"classes={len(changed_classes)} | conflicts={len(conflicts)}"
            )
        else:
            if v1 is None:
                record["status"] = "TARGET_TEXT_NOT_FOUND"
                result["modified"].append(record)
                summary.append(f"[TARGET_TEXT_NOT_FOUND] {logical}")
                continue

            v3_hash = sha256_file(v3)
            v1_hash = sha256_file(v1)
            if v1_hash == v3_hash:
                status = "TEXT_CHANGE_CAN_BE_REAPPLIED"
            else:
                status = "TEXT_MANUAL_MERGE_REQUIRED"

            record["status"] = status
            safe_name = logical.replace("/", "__")
            if Path(logical).suffix.lower() in TEXT_EXTS:
                write_text_diff(
                    analysis_dir / "text-diffs" / f"{safe_name}.RC1_vs_V3.diff",
                    v3, rc1, "official-1.4.60V3", "community-RC1",
                )
                write_text_diff(
                    analysis_dir / "text-diffs" / f"{safe_name}.V1_vs_V3.diff",
                    v3, v1, "official-1.4.60V3", "official-1.4.61V1",
                )
            summary.append(f"[{status}] {logical}")

        result["modified"].append(record)

    for item in community_only:
        logical = item["path"]
        rc1 = rc1_index.get(logical)
        record = {"path": logical}
        if rc1 is None:
            record["status"] = "INDEX_ERROR"
            result["community_only"].append(record)
            continue

        relocated = same_hash_elsewhere(rc1, v3_index)
        if relocated:
            record["status"] = "PACKAGING_RELOCATION_NOT_CUSTOM_CODE"
            record["official_equivalents"] = relocated
        elif logical.startswith("mage-client/config/deck-downloader/"):
            record["status"] = "SAFE_COMMUNITY_OVERLAY"
        elif logical.lower().endswith(".jar"):
            record["status"] = "COMMUNITY_JAR_REVIEW_REQUIRED"
        else:
            record["status"] = "COMMUNITY_FILE_REVIEW_REQUIRED"
        result["community_only"].append(record)
        summary.append(f"[{record['status']}] {logical}")

    counts = {}
    for group in (result["modified"], result["community_only"]):
        for rec in group:
            s = rec.get("status", "UNKNOWN")
            counts[s] = counts.get(s, 0) + 1
    result["counts"] = counts

    (analysis_dir / "migration-analysis.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    summary += ["", "STATUS COUNTS"]
    for k in sorted(counts):
        summary.append(f"{k}: {counts[k]}")
    summary += [
        "",
        "NEXT RULE:",
        "Do NOT activate 1.4.61V1 yet. JAR changes must be reconstructed at source level,",
        "and any JAR conflict must be ported against the new upstream code before build/test.",
    ]
    (analysis_dir / "RESUMEN_MIGRACION_3VIAS.txt").write_text(
        "\n".join(summary) + "\n", encoding="utf-8"
    )

    print("Analysis complete.")
    print(f"Summary: {analysis_dir / 'RESUMEN_MIGRACION_3VIAS.txt'}")
    print(f"JSON:    {analysis_dir / 'migration-analysis.json'}")
    print("\n1.4.61V1 remains BLOCKED. Active XMage was not modified.")
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
