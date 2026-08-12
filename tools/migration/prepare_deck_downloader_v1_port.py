#!/usr/bin/env python3
"""Prepare and compile the Deck Downloader port on official XMage 1.4.61V1.

SAFE MODE:
- clones official magefree/mage into migration-workspace/port-1.4.61V1
- verifies exact official commit 105d560ece2939d03fe6d052d3479a91c04ca4b2
- copies the cleaned DeckDownloaderPane source
- injects the minimal MageFrame toolbar integration
- copies the captured RC1 runtime into Mage.Client/release/config/deck-downloader
- validates Python syntax/runtime files
- compiles Mage.Client and dependencies in the isolated source tree
- NEVER modifies active XMage or the clean V1 staging installation
"""
from __future__ import annotations

import hashlib
import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

WORKSPACE = "migration-workspace"
OFFICIAL_REPO = "https://github.com/magefree/mage.git"
OFFICIAL_TAG = "xmage_1.4.61V1"
OFFICIAL_COMMIT = "105d560ece2939d03fe6d052d3479a91c04ca4b2"


def run(cmd, cwd=None, timeout=3600):
    print("$", " ".join(map(str, cmd)))
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          encoding="utf-8", errors="replace", timeout=timeout)


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_runtime_snapshot(ws: Path) -> Path:
    candidates = []
    for p in (ws / "expanded-community").rglob("deck-downloader"):
        if p.is_dir() and p.as_posix().lower().endswith("mage-client/config/deck-downloader"):
            candidates.append(p)
    if not candidates:
        raise RuntimeError("Deck Downloader runtime snapshot not found. Run runtime capture first.")
    return max(candidates, key=lambda p: sum(1 for x in p.rglob("*") if x.is_file()))


def inject_mageframe(path: Path):
    text = path.read_text(encoding="utf-8")
    if "mage.client.decks.DeckDownloaderPane" not in text:
        anchor = "import mage.client.deckeditor.collection.viewer.CollectionViewerPane;\n"
        if text.count(anchor) != 1:
            raise RuntimeError("MageFrame import anchor not found exactly once")
        text = text.replace(anchor, anchor + "import mage.client.decks.DeckDownloaderPane;\n", 1)

    marker = 'JButton btnDeckLibrary = new JButton("Descargar decks");'
    if marker not in text:
        anchor = "        mageToolbar.add(createSwitchPanelsButton(), 0);\n        mageToolbar.add(new javax.swing.JToolBar.Separator(), 1);\n"
        if text.count(anchor) != 1:
            raise RuntimeError("MageFrame toolbar anchor not found exactly once")
        block = anchor + "\n" + \
'''        JButton btnDeckLibrary = new JButton("Descargar decks");
        btnDeckLibrary.setToolTipText("Actualizar la biblioteca histórica de mazos");
        btnDeckLibrary.setFocusable(false);
        btnDeckLibrary.addActionListener(event -> DeckDownloaderPane.showPane());
        int deckButtonIndex = mageToolbar.getComponentIndex(btnDeckEditor);
        mageToolbar.add(btnDeckLibrary, deckButtonIndex + 2);
        mageToolbar.add(new javax.swing.JToolBar.Separator(), deckButtonIndex + 3);
'''
        text = text.replace(anchor, block, 1)

    path.write_text(text, encoding="utf-8")


def main():
    here = Path(__file__).resolve().parent
    repo_root = here.parent.parent
    ws = here / WORKSPACE
    work = ws / "port-1.4.61V1"
    source = work / "source"
    reports = work / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    print("=== XMage Community Patch - PREPARE DECK DOWNLOADER PORT TO 1.4.61V1 ===")
    print("SAFE MODE: isolated source tree only.\n")

    if shutil.which("git") is None:
        raise RuntimeError("git was not found on PATH")

    if source.exists():
        shutil.rmtree(source)

    clone = run(["git", "clone", "--branch", OFFICIAL_TAG, "--depth", "1", OFFICIAL_REPO, str(source)], timeout=1800)
    (reports / "git-clone.log").write_text(clone.stdout, encoding="utf-8")
    if clone.returncode != 0:
        raise RuntimeError("Official source clone failed; see git-clone.log")

    rev = run(["git", "rev-parse", "HEAD"], cwd=source, timeout=60)
    head = rev.stdout.strip().splitlines()[-1] if rev.returncode == 0 else ""
    if head != OFFICIAL_COMMIT:
        raise RuntimeError(f"Official commit mismatch: expected {OFFICIAL_COMMIT}, got {head}")
    print(f"[OK] Official 1.4.61V1 commit verified: {head}")

    pane_src = repo_root / "patches" / "1.4.61V1" / "deck-downloader" / "Mage.Client" / "src" / "main" / "java" / "mage" / "client" / "decks" / "DeckDownloaderPane.java"
    if not pane_src.exists():
        raise RuntimeError(f"Missing clean DeckDownloaderPane source: {pane_src}")
    pane_dst = source / "Mage.Client" / "src" / "main" / "java" / "mage" / "client" / "decks" / "DeckDownloaderPane.java"
    pane_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pane_src, pane_dst)

    mageframe = source / "Mage.Client" / "src" / "main" / "java" / "mage" / "client" / "MageFrame.java"
    inject_mageframe(mageframe)

    runtime_src = find_runtime_snapshot(ws)
    runtime_dst = source / "Mage.Client" / "release" / "config" / "deck-downloader"
    if runtime_dst.exists():
        shutil.rmtree(runtime_dst)
    shutil.copytree(runtime_src, runtime_dst)

    requirements = runtime_dst / "requirements.txt"
    requirements.write_text("requests\nbeautifulsoup4\nselenium\nundetected-chromedriver\nsetuptools\n", encoding="utf-8")

    runtime_records = []
    for py in sorted(runtime_dst.glob("*.py")):
        py_compile.compile(str(py), doraise=True)
        runtime_records.append({"path": py.relative_to(source).as_posix(), "sha256": sha256(py)})
    if not (runtime_dst / "deck_library_updater.py").exists():
        raise RuntimeError("deck_library_updater.py missing after runtime copy")

    # Verify assembly really includes release/ into the final client distribution.
    assembly = source / "Mage.Client" / "src" / "main" / "assembly" / "distribution.xml"
    assembly_text = assembly.read_text(encoding="utf-8")
    if "<directory>release/</directory>" not in assembly_text:
        raise RuntimeError("Official client assembly no longer includes Mage.Client/release; packaging path unsafe")

    mvn = shutil.which("mvn") or shutil.which("mvn.cmd")
    if not mvn:
        raise RuntimeError("Maven (mvn) was not found on PATH")

    build = run([mvn, "-pl", "Mage.Client", "-am", "-DskipTests", "package"], cwd=source, timeout=7200)
    (reports / "maven-build.log").write_text(build.stdout, encoding="utf-8")

    result = {
        "schema": 1,
        "official_tag": OFFICIAL_TAG,
        "official_commit": head,
        "runtime_files": runtime_records,
        "deck_downloader_source_sha256": sha256(pane_dst),
        "mageframe_sha256": sha256(mageframe),
        "build_returncode": build.returncode,
        "build_ok": build.returncode == 0,
        "active_xmage_modified": False,
        "clean_v1_staging_modified": False,
    }
    (reports / "port-build-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    summary = [
        "XMage Community Patch - 1.4.61V1 DECK DOWNLOADER PORT BUILD",
        "==========================================================",
        "",
        f"Official tag: {OFFICIAL_TAG}",
        f"Official commit verified: {head}",
        f"Runtime Python files validated: {len(runtime_records)}",
        f"Maven build return code: {build.returncode}",
        f"BUILD OK: {build.returncode == 0}",
        "",
        "SAFE MODE: active XMage and clean 1.4.61V1 staging were not modified.",
        "1.4.61V1 remains BLOCKED until build + packaging + smoke tests pass.",
        "",
        f"Build log: {reports / 'maven-build.log'}",
    ]
    (reports / "RESUMEN_PORT_BUILD.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")

    print("\n=== RESULT ===")
    print(f"Runtime Python files validated: {len(runtime_records)}")
    print(f"Maven build return code: {build.returncode}")
    print(f"BUILD OK: {build.returncode == 0}")
    print(f"Summary: {reports / 'RESUMEN_PORT_BUILD.txt'}")
    print("Active XMage was not modified. 1.4.61V1 remains BLOCKED.")
    return 0 if build.returncode == 0 else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("Active XMage was not modified. 1.4.61V1 remains BLOCKED.")
        input("Press Enter to close...")
        raise SystemExit(1)
