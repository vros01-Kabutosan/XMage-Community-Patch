#!/usr/bin/env python3
"""Safe migration audit for XMage Community Patch.

This tool NEVER overwrites an active XMage installation. It downloads the
published RC1 Complete package plus clean official XMage releases, extracts them
into an isolated workspace, compares RC1 against the official 1.4.60V3 base,
and prepares a clean 1.4.61V1 staging tree for later patch reconstruction.

Python 3 standard library only.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
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
    req = urllib.request.Request(url, headers={"User-Agent": "XMage-Community-Patch-Migration-Audit/1.0"})
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


def safe_extract(zip_path: Path, dest: Path) -> None:
    marker = dest / ".extracted-ok"
    if marker.exists():
        print(f"[OK] Reusing extracted {dest.name}")
        return
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    print(f"[EXTRACT] {zip_path.name}")
    with zipfile.ZipFile(zip_path) as zf:
        root = dest.resolve()
        for info in zf.infolist():
            target = (dest / info.filename).resolve()
            if root not in target.parents and target != root:
                raise RuntimeError(f"Unsafe ZIP path: {info.filename}")
        zf.extractall(dest)
    marker.write_text("ok\n", encoding="utf-8")


def payload_root(extracted: Path) -> Path:
    """Strip harmless single wrapper directories while preserving XMage layout."""
    ignored = {".extracted-ok"}
    current = extracted
    for _ in range(4):
        entries = [p for p in current.iterdir() if p.name not in ignored]
        dirs = [p for p in entries if p.is_dir()]
        files = [p for p in entries if p.is_file()]
        if len(dirs) == 1 and not files:
            current = dirs[0]
        else:
            break
    return current


def manifest(root: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for base, dirs, files in os.walk(root):
        dirs.sort(key=str.lower)
        files.sort(key=str.lower)
        for name in files:
            path = Path(base) / name
            if name == ".extracted-ok":
                continue
            rel = path.relative_to(root).as_posix()
            result[rel] = {
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
    return result


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
        })
    return rows


def write_reports(report_dir: Path, rows, roots: dict[str, str]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    json_report = {
        "schema": 1,
        "generated_unix": int(time.time()),
        "comparison": "Community RC1 Complete vs official xmage_1.4.60V3 binary release",
        "roots": roots,
        "counts": counts,
        "attention": [r for r in rows if r["status"] != "IDENTICAL"],
    }
    (report_dir / "rc1-vs-upstream-v3.json").write_text(
        json.dumps(json_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    fields = [
        "path", "status", "upstream_sha256", "community_sha256",
        "upstream_size", "community_size",
    ]
    with (report_dir / "rc1-vs-upstream-v3.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    txt = [
        "XMage Community Patch - RC1 migration audit",
        "================================================",
        "",
        "This audit DOES NOT modify your active XMage installation.",
        "",
    ]
    for key in ("MODIFIED", "COMMUNITY_ONLY", "UPSTREAM_ONLY", "IDENTICAL"):
        txt.append(f"{key}: {counts.get(key, 0)}")
    txt += ["", "Files requiring review:"]
    for row in rows:
        if row["status"] != "IDENTICAL":
            txt.append(f"[{row['status']}] {row['path']}")
    (report_dir / "RESUMEN_AUDITORIA.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    workspace = script_dir / WORKSPACE_NAME
    downloads = workspace / "downloads"
    extracted = workspace / "extracted"
    reports = workspace / "reports"
    staging = workspace / "staging" / "xmage_1.4.61V1-clean"

    downloads.mkdir(parents=True, exist_ok=True)

    rc1_zip = downloads / "rc1.zip"
    v3_zip = downloads / "upstream-v3.zip"
    v1_zip = downloads / "upstream-v1.zip"

    print("=== XMage Community Patch - PROTECTED MIGRATION AUDIT ===")
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
    print(f"[SCAN] Community root: {rc1_root}")
    print(f"[SCAN] Upstream V3 root: {v3_root}")

    community_manifest = manifest(rc1_root)
    upstream_manifest = manifest(v3_root)
    rows = compare(upstream_manifest, community_manifest)
    write_reports(reports, rows, {
        "community_rc1": str(rc1_root),
        "upstream_v3": str(v3_root),
    })

    # Prepare clean 1.4.61V1 candidate ONLY in staging. Never overlay RC1 here.
    safe_extract(v1_zip, staging)
    v1_root = payload_root(staging)
    (reports / "staging-info.json").write_text(
        json.dumps({
            "schema": 1,
            "upstream_tag": "xmage_1.4.61V1",
            "upstream_commit": "105d560ece2939d03fe6d052d3479a91c04ca4b2",
            "staging_root": str(v1_root),
            "status": "CLEAN_UPSTREAM_ONLY_DO_NOT_ACTIVATE",
        }, indent=2),
        encoding="utf-8",
    )

    attention = [r for r in rows if r["status"] != "IDENTICAL"]
    print("\n=== DONE ===")
    print(f"Files requiring review: {len(attention)}")
    print(f"Report: {reports / 'RESUMEN_AUDITORIA.txt'}")
    print(f"JSON:   {reports / 'rc1-vs-upstream-v3.json'}")
    print(f"CSV:    {reports / 'rc1-vs-upstream-v3.csv'}")
    print(f"Clean V1 staging prepared at: {v1_root}")
    print("\nIMPORTANT: V1 remains BLOCKED. Nothing has been copied into your active XMage.")
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
