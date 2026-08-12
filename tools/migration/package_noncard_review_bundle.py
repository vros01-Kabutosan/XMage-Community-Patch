#!/usr/bin/env python3
"""Package the 14 actionable non-card migration cases into one deterministic ZIP.

SAFE MODE:
- reads only migration-workspace reports/evidence
- writes one review bundle ZIP under reports/migration-analysis/review-bundle
- never modifies active XMage
- never modifies 1.4.61V1 staging
- never applies patches

Bundle contains, for actionable sources only:
- RC1 reconstructed Java
- official V3 reconstructed Java when available
- official V1 reconstructed Java when available
- V3->RC1, V3->V1, RC1->V1 diffs
- clean GameReplay candidate patch
- manifest with SHA-256 checksums
- source-threeway and port-plan summaries
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path

WORKSPACE = "migration-workspace"
BUNDLE_NAME = "XMage_RC1_to_1.4.61V1_NONCARD_REVIEW_BUNDLE.zip"


def load(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(f"Missing required input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(source: str) -> str:
    return source.replace("/", "__").replace("\\", "__").replace(":", "_")


def find_unique_source(root: Path, java_entry: str) -> Path | None:
    direct = root / java_entry
    if direct.exists():
        return direct
    matches = list(root.rglob(Path(java_entry).name)) if root.exists() else []
    return matches[0] if len(matches) == 1 else None


def copy_record(src: Path | None, dst: Path, manifest_files: list[dict], label: str) -> None:
    if src is None or not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    manifest_files.append({
        "label": label,
        "path": dst.as_posix(),
        "sha256": sha256(dst),
        "size": dst.stat().st_size,
    })


def main() -> int:
    here = Path(__file__).resolve().parent
    reports = here / WORKSPACE / "reports" / "migration-analysis"
    threeway = load(reports / "source-threeway" / "source-threeway.json")
    port_plan = load(reports / "port-plan-noncard" / "noncard-port-plan.json")
    recon = load(reports / "source-reconstruction" / "reconstruction.json")

    source_threeway_root = reports / "source-threeway"
    recon_root = reports / "source-reconstruction"
    out_root = reports / "review-bundle"
    staging = out_root / "bundle"
    if out_root.exists():
        shutil.rmtree(out_root)
    staging.mkdir(parents=True, exist_ok=True)

    print("=== XMage Community Patch - NON-CARD REVIEW BUNDLE ===")
    print("SAFE MODE: packaging evidence only.\n")

    actionable = [
        r for r in threeway.get("rows", [])
        if r.get("action") in {"PORT_COMMUNITY_CHANGE", "REAL_CONFLICT", "REVIEW_REQUIRED"}
    ]
    if len(actionable) != 14:
        print(f"[WARN] Expected 14 actionable sources, found {len(actionable)}")

    manifest_files: list[dict] = []
    manifest_sources: list[dict] = []

    # Map official decompile roots from java source path and jar stem heuristically.
    v3_base = recon_root / "official-threeway-decompiled" / "v3"
    v1_base = recon_root / "official-threeway-decompiled" / "v1"
    rc1_base = recon_root / "selected-noncard-sources"
    diff_base = source_threeway_root / "diffs"

    for index, row in enumerate(actionable, 1):
        source = row["source"]
        java_entry = row.get("java_entry", "")
        action = row["action"]
        case_dir = staging / "cases" / f"{index:02d}_{safe_name(source)}"
        case_dir.mkdir(parents=True, exist_ok=True)

        rc1_src = rc1_base / source

        # Find matching official source under all per-JAR CFR directories.
        v3_matches = []
        if v3_base.exists():
            for jar_dir in v3_base.iterdir():
                if jar_dir.is_dir():
                    p = find_unique_source(jar_dir, java_entry)
                    if p:
                        v3_matches.append(p)
        v1_matches = []
        if v1_base.exists():
            for jar_dir in v1_base.iterdir():
                if jar_dir.is_dir():
                    p = find_unique_source(jar_dir, java_entry)
                    if p:
                        v1_matches.append(p)
        v3_src = v3_matches[0] if len(v3_matches) == 1 else None
        v1_src = v1_matches[0] if len(v1_matches) == 1 else None

        copy_record(v3_src, case_dir / "official_1.4.60V3.java", manifest_files, f"{source}:V3")
        copy_record(rc1_src if rc1_src.exists() else None, case_dir / "community_RC1.java", manifest_files, f"{source}:RC1")
        copy_record(v1_src, case_dir / "official_1.4.61V1.java", manifest_files, f"{source}:V1")

        stem = safe_name(source)
        diff_names = []
        for suffix in ("V3_to_RC1", "V3_to_V1", "RC1_to_V1"):
            src = diff_base / f"{stem}.{suffix}.diff"
            if src.exists():
                dst = case_dir / f"{suffix}.diff"
                copy_record(src, dst, manifest_files, f"{source}:{suffix}")
                diff_names.append(dst.name)

        candidate_patch = None
        if action == "PORT_COMMUNITY_CHANGE":
            for candidate in (reports / "port-plan-noncard" / "candidate-patches").glob("*.patch"):
                if Path(source).name in candidate.name or len(list((reports / "port-plan-noncard" / "candidate-patches").glob("*.patch"))) == 1:
                    target = case_dir / "candidate.patch"
                    copy_record(candidate, target, manifest_files, f"{source}:candidate-patch")
                    candidate_patch = target.name
                    break

        case_info = {
            "index": index,
            "action": action,
            "subsystem": row.get("subsystem", ""),
            "source": source,
            "java_entry": java_entry,
            "rc1_jar": row.get("rc1_jar", ""),
            "target_jar": row.get("target_jar", ""),
            "included": {
                "v3_java": v3_src is not None,
                "rc1_java": rc1_src.exists(),
                "v1_java": v1_src is not None,
                "diffs": diff_names,
                "candidate_patch": candidate_patch,
            },
        }
        manifest_sources.append(case_info)
        (case_dir / "CASE.json").write_text(json.dumps(case_info, indent=2, ensure_ascii=False), encoding="utf-8")

    # Add summaries and machine-readable plans.
    top_files = [
        reports / "source-threeway" / "RESUMEN_SOURCE_THREEWAY.txt",
        reports / "port-plan-noncard" / "NONCARD_PORT_PLAN.txt",
        reports / "source-threeway" / "SOURCE_THREEWAY_CLASSIFICATION.csv",
        reports / "port-plan-noncard" / "noncard-port-plan.json",
    ]
    for src in top_files:
        if src.exists():
            copy_record(src, staging / "metadata" / src.name, manifest_files, f"metadata:{src.name}")

    manifest = {
        "schema": 1,
        "purpose": "XMage RC1 -> 1.4.61V1 non-card migration review bundle",
        "safe_mode": True,
        "active_xmage_modified": False,
        "v1_staging_modified": False,
        "actionable_sources": len(actionable),
        "sources": manifest_sources,
        "files": [],
    }

    # Recompute paths relative to bundle root for deterministic manifest.
    relative_files = []
    for rec in manifest_files:
        p = Path(rec["path"])
        try:
            rel = p.relative_to(staging).as_posix()
        except ValueError:
            continue
        relative_files.append({**rec, "path": rel})
    relative_files.sort(key=lambda x: x["path"].lower())
    manifest["files"] = relative_files
    manifest_path = staging / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    readme = [
        "XMage RC1 -> 1.4.61V1 NON-CARD REVIEW BUNDLE",
        "================================================",
        "",
        "Contains ONLY the actionable non-card migration cases.",
        "No patch has been applied to XMage or to 1.4.61V1 staging.",
        "",
        f"Actionable sources: {len(actionable)}",
        f"Clean port candidates: {sum(1 for r in actionable if r['action']=='PORT_COMMUNITY_CHANGE')}",
        f"Real conflicts: {sum(1 for r in actionable if r['action']=='REAL_CONFLICT')}",
        f"Review required: {sum(1 for r in actionable if r['action']=='REVIEW_REQUIRED')}",
        "",
        "Each case folder may contain V3, RC1 and V1 reconstructed Java plus three unified diffs.",
        "MANIFEST.json contains SHA-256 checksums for integrity.",
        "",
        "1.4.61V1 REMAINS BLOCKED.",
    ]
    (staging / "README.txt").write_text("\n".join(readme) + "\n", encoding="utf-8")

    zip_path = out_root / BUNDLE_NAME
    # Deterministic-ish ordering; preserve actual timestamps is not important for evidence.
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(staging.rglob("*"), key=lambda x: x.relative_to(staging).as_posix().lower()):
            if p.is_file():
                zf.write(p, p.relative_to(staging).as_posix())

    zip_hash = sha256(zip_path)
    summary = [
        "XMage Community Patch - NON-CARD REVIEW BUNDLE",
        "===============================================",
        "",
        "SAFE MODE: no patch applied; active XMage and 1.4.61V1 staging were not modified.",
        f"Actionable sources packaged: {len(actionable)}",
        f"ZIP: {zip_path}",
        f"ZIP SHA-256: {zip_hash}",
        "",
        "Upload this single ZIP to the project maintainer for source-level merge review.",
        "1.4.61V1 remains BLOCKED.",
    ]
    summary_path = out_root / "RESUMEN_REVIEW_BUNDLE.txt"
    summary_path.write_text("\n".join(summary) + "\n", encoding="utf-8")

    print(f"Actionable sources packaged: {len(actionable)}")
    print(f"ZIP: {zip_path}")
    print(f"SHA-256: {zip_hash}")
    print(f"Summary: {summary_path}")
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
