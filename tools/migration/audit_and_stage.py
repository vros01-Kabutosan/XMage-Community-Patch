#!/usr/bin/env python3
"""Safe migration audit for XMage Community Patch.

This tool NEVER overwrites an active XMage installation.

It downloads/verifies the published RC1 Complete package and clean official
XMage releases, expands the RC1 nested Client/Server ZIPs, normalizes the
internal XMage directory layout, compares RC1 against official 1.4.60V3, and
prepares a clean 1.4.61V1 staging tree for later patch reconstruction.

Python 3 standard library only.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import time
import urllib.request
import zipfile
from pathlib import Path

RC1_URL = (
    "https://github.com/vros01-Kabutosan/XMage-Community-Patch/releases/download/"
    "v1.4.60V3-community-patch-rc1/"
    "XMage_Community_Patch_1.4.60-V3-RC1_Complete_Windows.zip"
)
UPSTREAM_V3_URL = (
    "https://github.com/magefree/mage/releases/download/xmage_1.4.60V3/"
    "mage-full_1.4.60-dev_2026-07-11_16-06.zip"
)
UPSTREAM_V1_URL = (
    "https://github.com/magefree/mage/releases/download/xmage_1.4.61V1/"
    "mage-full_1.4.61-dev_2026-08-12_12-34.zip"
)

EXPECTED_SHA256 = {
    "rc1.zip": "17997a7f2e00fb52515c17a2c2bdb5b554ef82efedca88a7702bac616c67ec0a",
    "upstream-v3.zip": "6a433bf5ec9bb4c61198695392221ca6cee15ebfbb2c55ee73093ea4b548865f",
    "upstream-v1.zip": "2aded65b0eb439e38edd529ba5230f0bd8b44e46f639f745b8ca73584a5ffd98",
}

WORKSPACE_NAME = "migration-workspace"
CHUNK = 1024 * 1024
PAYLOAD_ANCHORS = ("mage-client", "mage-server")
TOP_LEVEL_XMAGE_FILES = {
    "installed.properties",
    "run-launcher-and-wait.cmd",
    "run-LAUNCHER.cmd",
    "XMageLauncher-0.3.8.jar",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dst: Path) -> None:
    if dst.exists():
        actual = sha256_file(dst)
        expected = EXPECTED_SHA256.get(dst.name)
        if expected and actual.lower() == expected.lower():
            print(f"[OK] Reusing verified {dst.name}")
            return
        print(f"[WARN] Existing {dst.name} hash mismatch; downloading again")
        dst.unlink()

    print(f"[DOWNLOAD] {dst.name}")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "XMage-Community-Patch-Migration-Audit/2.1"},
    )
    tmp = dst.with_suffix(dst.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as out:
        total = int(response.headers.get("Content-Length", "0") or 0)
        done = 0
        last_pct = -1
        while True:
            data = response.read(CHUNK)
            if not data:
                break
            out.write(data)
            done += len(data)
            if total:
                pct = int(done * 100 / total)
                if pct != last_pct and (pct % 5 == 0 or pct == 100):
                    print(f"  {pct}%")
                    last_pct = pct
    tmp.replace(dst)

    actual = sha256_file(dst)
    expected = EXPECTED_SHA256.get(dst.name)
    if expected and actual.lower() != expected.lower():
        dst.unlink(missing_ok=True)
        raise RuntimeError(f"SHA-256 mismatch for {dst.name}: {actual}")
    print(f"[OK] SHA-256 verified: {dst.name}")


def safe_extract(zip_path: Path, dest: Path, force: bool = False) -> None:
    marker = dest / ".extracted-ok"
    if marker.exists() and not force:
        print(f"[OK] Reusing extracted {dest.name}")
        return
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    print(f"[EXTRACT] {zip_path.name} -> {dest.name}")
    with zipfile.ZipFile(zip_path) as zf:
        root = dest.resolve()
        for info in zf.infolist():
            target = (dest / info.filename).resolve()
            if root not in target.parents and target != root:
                raise RuntimeError(f"Unsafe ZIP path: {info.filename}")
        zf.extractall(dest)
    marker.write_text("ok\n", encoding="utf-8")


def payload_root(extracted: Path) -> Path:
    """Remove harmless single wrapper directories only."""
    ignored = {".extracted-ok"}
    current = extracted
    for _ in range(6):
        entries = [p for p in current.iterdir() if p.name not in ignored]
        dirs = [p for p in entries if p.is_dir()]
        files = [p for p in entries if p.is_file()]
        if len(dirs) == 1 and not files:
            current = dirs[0]
        else:
            break
    return current


def normalize_rel(rel: str) -> str | None:
    """Map different packaging wrappers to one logical XMage path."""
    parts = [p for p in Path(rel).parts if p not in (".", "")]
    lower = [p.lower() for p in parts]

    for anchor in PAYLOAD_ANCHORS:
        if anchor in lower:
            idx = lower.index(anchor)
            return "/".join(parts[idx:])

    if parts and parts[-1] in TOP_LEVEL_XMAGE_FILES:
        return parts[-1]

    return None


def add_tree_to_manifest(
    root: Path,
    result: dict[str, dict[str, object]],
    source_label: str,
) -> None:
    # If payload_root() already descended *into* mage-client/mage-server,
    # preserve that directory name explicitly. Otherwise normalization can
    # discover the anchor from the relative path as before.
    root_anchor = root.name.lower() if root.name.lower() in PAYLOAD_ANCHORS else None

    for base, dirs, files in os.walk(root):
        dirs.sort(key=str.lower)
        files.sort(key=str.lower)
        for name in files:
            path = Path(base) / name
            if name == ".extracted-ok":
                continue
            raw_rel = path.relative_to(root).as_posix()
            if root_anchor:
                logical = f"{root.name}/{raw_rel}"
            else:
                logical = normalize_rel(raw_rel)
            if logical is None:
                continue
            entry = {
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
                "source": source_label,
                "source_path": raw_rel,
            }
            old = result.get(logical)
            if old and old["sha256"] != entry["sha256"]:
                raise RuntimeError(
                    f"Conflicting files map to the same logical path: {logical}\n"
                    f"  old: {old['source']}::{old['source_path']}\n"
                    f"  new: {source_label}::{raw_rel}"
                )
            result[logical] = entry


def official_manifest(root: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    add_tree_to_manifest(root, result, "official")
    if not result:
        raise RuntimeError("Could not locate mage-client/mage-server payload in official package")
    return result


def community_manifest(rc1_root: Path, expanded_dir: Path) -> tuple[dict[str, dict[str, object]], list[str]]:
    """Expand nested RC1 Client/Server packages and build one logical manifest."""
    result: dict[str, dict[str, object]] = {}
    nested = []

    candidates = []
    for p in rc1_root.rglob("*.zip"):
        n = p.name.lower()
        if "xmage_community_patch" in n and ("client_windows" in n or "server_windows" in n):
            candidates.append(p)

    if not candidates:
        raise RuntimeError(
            "RC1 Complete package does not contain the expected nested Client/Server ZIPs"
        )

    if expanded_dir.exists():
        shutil.rmtree(expanded_dir)
    expanded_dir.mkdir(parents=True, exist_ok=True)

    for index, nested_zip in enumerate(sorted(candidates, key=lambda p: p.name.lower()), start=1):
        label = "client" if "client_windows" in nested_zip.name.lower() else "server"
        dest = expanded_dir / f"{index:02d}-{label}"
        safe_extract(nested_zip, dest, force=True)
        root = payload_root(dest)
        add_tree_to_manifest(root, result, f"community-{label}")
        nested.append(str(nested_zip))
        print(f"[NORMALIZE] {label}: {root}")

    if not result:
        raise RuntimeError("Nested RC1 packages were extracted but no XMage payload was detected")
    return result, nested


def compare(base: dict[str, dict[str, object]], community: dict[str, dict[str, object]]):
    rows = []
    all_paths = sorted(set(base) | set(community), key=str.lower)
    for rel in all_paths:
        b = base.get(rel)
        c = community.get(rel)
        if b is None:
            status = "COMMUNITY_ONLY"
        elif c is None:
            status = "UPSTREAM_ONLY"
        elif b["sha256"] == c["sha256"]:
            status = "IDENTICAL"
        else:
            status = "MODIFIED"
        rows.append({
            "path": rel,
            "status": status,
            "upstream_sha256": b["sha256"] if b else "",
            "community_sha256": c["sha256"] if c else "",
            "upstream_size": b["size"] if b else "",
            "community_size": c["size"] if c else "",
            "upstream_source_path": b["source_path"] if b else "",
            "community_source_path": c["source_path"] if c else "",
        })
    return rows


def write_reports(report_dir: Path, rows, metadata: dict[str, object]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    json_report = {
        "schema": 2,
        "generated_unix": int(time.time()),
        "comparison": "Community RC1 nested Client/Server payload vs official xmage_1.4.60V3",
        "metadata": metadata,
        "counts": counts,
        "attention": [r for r in rows if r["status"] != "IDENTICAL"],
    }
    (report_dir / "rc1-vs-upstream-v3.json").write_text(
        json.dumps(json_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    fields = [
        "path", "status", "upstream_sha256", "community_sha256",
        "upstream_size", "community_size", "upstream_source_path",
        "community_source_path",
    ]
    with (report_dir / "rc1-vs-upstream-v3.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    txt = [
        "XMage Community Patch - RC1 migration audit v2.1",
        "=====================================================",
        "",
        "This audit DOES NOT modify your active XMage installation.",
        "RC1 nested Client/Server packages were expanded and XMage paths normalized.",
        "",
    ]
    for key in ("MODIFIED", "COMMUNITY_ONLY", "UPSTREAM_ONLY", "IDENTICAL"):
        txt.append(f"{key}: {counts.get(key, 0)}")
    txt += ["", "Files requiring review:"]
    for row in rows:
        if row["status"] != "IDENTICAL":
            txt.append(f"[{row['status']}] {row['path']}")
    (report_dir / "RESUMEN_AUDITORIA.txt").write_text(
        "\n".join(txt) + "\n", encoding="utf-8"
    )


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    workspace = script_dir / WORKSPACE_NAME
    downloads = workspace / "downloads"
    extracted = workspace / "extracted"
    expanded = workspace / "expanded-community"
    reports = workspace / "reports"
    staging = workspace / "staging" / "xmage_1.4.61V1-clean"

    downloads.mkdir(parents=True, exist_ok=True)

    rc1_zip = downloads / "rc1.zip"
    v3_zip = downloads / "upstream-v3.zip"
    v1_zip = downloads / "upstream-v1.zip"

    print("=== XMage Community Patch - PROTECTED MIGRATION AUDIT v2.1 ===")
    print("SAFE MODE: your active XMage installation will NOT be touched.\n")

    download(RC1_URL, rc1_zip)
    download(UPSTREAM_V3_URL, v3_zip)
    download(UPSTREAM_V1_URL, v1_zip)

    rc1_extract = extracted / "community-rc1"
    v3_extract = extracted / "upstream-v3"
    safe_extract(rc1_zip, rc1_extract)
    safe_extract(v3_zip, v3_extract)

    rc1_root = payload_root(rc1_extract)
    v3_root = payload_root(v3_extract)
    print(f"[SCAN] RC1 Complete root: {rc1_root}")
    print(f"[SCAN] Official V3 root:  {v3_root}")

    community, nested_zips = community_manifest(rc1_root, expanded)
    upstream = official_manifest(v3_root)

    print(f"[OK] Logical RC1 payload files: {len(community)}")
    print(f"[OK] Logical official V3 files: {len(upstream)}")

    rows = compare(upstream, community)
    write_reports(
        reports,
        rows,
        {
            "rc1_complete_root": str(rc1_root),
            "official_v3_root": str(v3_root),
            "nested_rc1_packages": nested_zips,
            "logical_rc1_files": len(community),
            "logical_upstream_files": len(upstream),
        },
    )

    safe_extract(v1_zip, staging)
    v1_root = payload_root(staging)
    v1_manifest = official_manifest(v1_root)
    (reports / "staging-info.json").write_text(
        json.dumps(
            {
                "schema": 2,
                "upstream_tag": "xmage_1.4.61V1",
                "upstream_commit": "105d560ece2939d03fe6d052d3479a91c04ca4b2",
                "staging_root": str(v1_root),
                "logical_payload_files": len(v1_manifest),
                "status": "CLEAN_UPSTREAM_ONLY_DO_NOT_ACTIVATE",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    print("\n=== DONE ===")
    print(f"IDENTICAL:      {counts.get('IDENTICAL', 0)}")
    print(f"MODIFIED:       {counts.get('MODIFIED', 0)}")
    print(f"COMMUNITY_ONLY: {counts.get('COMMUNITY_ONLY', 0)}")
    print(f"UPSTREAM_ONLY:  {counts.get('UPSTREAM_ONLY', 0)}")
    print(f"Report: {reports / 'RESUMEN_AUDITORIA.txt'}")
    print(f"JSON:   {reports / 'rc1-vs-upstream-v3.json'}")
    print(f"CSV:    {reports / 'rc1-vs-upstream-v3.csv'}")
    print(f"Clean V1 staging: {v1_root}")
    print("\nIMPORTANT: V1 remains BLOCKED. Nothing was copied into your active XMage.")
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
