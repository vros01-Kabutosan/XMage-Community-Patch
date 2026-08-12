#!/usr/bin/env python3
"""Prepare and compile the Deck Downloader port on official XMage 1.4.61V1.

SAFE MODE:
- downloads the exact official 1.4.61V1 commit archive into migration-workspace
- verifies the source archive is pinned to commit 105d560ece2939d03fe6d052d3479a91c04ca4b2
- copies the cleaned DeckDownloaderPane source
- injects the minimal MageFrame toolbar integration
- copies the captured RC1 runtime into Mage.Client/release/config/deck-downloader
- validates Python syntax/runtime files
- automatically locates Maven or bootstraps a verified isolated Apache Maven
- compiles Mage.Client and dependencies in the isolated source tree
- NEVER modifies active XMage or the clean V1 staging installation

No Git installation is required.
"""
from __future__ import annotations

import hashlib
import json
import os
import py_compile
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

WORKSPACE = "migration-workspace"
OFFICIAL_COMMIT = "105d560ece2939d03fe6d052d3479a91c04ca4b2"
OFFICIAL_TAG = "xmage_1.4.61V1"
OFFICIAL_ARCHIVE = f"https://codeload.github.com/magefree/mage/zip/{OFFICIAL_COMMIT}"

MAVEN_VERSION = "3.9.16"
MAVEN_BASE = f"https://archive.apache.org/dist/maven/maven-3/{MAVEN_VERSION}/binaries"
MAVEN_ZIP_NAME = f"apache-maven-{MAVEN_VERSION}-bin.zip"
MAVEN_ZIP_URL = f"{MAVEN_BASE}/{MAVEN_ZIP_NAME}"
MAVEN_SHA512_URL = MAVEN_ZIP_URL + ".sha512"


def run(cmd, cwd=None, timeout=3600, env=None):
    print("$", " ".join(map(str, cmd)))
    return subprocess.run(
        [str(x) for x in cmd], cwd=cwd, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        encoding="utf-8", errors="replace", timeout=timeout, env=env,
    )


def hash_file(path: Path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    print(f"[DOWNLOAD] {url}")
    with urllib.request.urlopen(url, timeout=120) as response, tmp.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(dest)


def prepare_official_source(tools: Path, source: Path, reports: Path):
    archive = tools / f"mage-{OFFICIAL_COMMIT}.zip"
    if not archive.exists():
        download(OFFICIAL_ARCHIVE, archive)
    if not zipfile.is_zipfile(archive):
        archive.unlink(missing_ok=True)
        raise RuntimeError("Downloaded official XMage source archive is not a valid ZIP")

    if source.exists():
        shutil.rmtree(source)
    extract_root = source.parent / "official-source-extract"
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True)

    print("[EXTRACT] exact official XMage commit archive")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(extract_root)

    roots = [p for p in extract_root.iterdir() if p.is_dir()]
    if len(roots) != 1:
        raise RuntimeError(f"Unexpected official source archive layout: {len(roots)} roots")
    extracted = roots[0]
    expected_fragment = OFFICIAL_COMMIT.lower()
    if expected_fragment not in extracted.name.lower():
        raise RuntimeError(f"Official source archive root does not contain pinned commit: {extracted.name}")
    shutil.move(str(extracted), str(source))
    shutil.rmtree(extract_root, ignore_errors=True)

    marker = source / "pom.xml"
    if not marker.exists():
        raise RuntimeError("Official source archive does not contain XMage pom.xml")

    archive_hash = hash_file(archive, "sha256")
    (reports / "official-source.json").write_text(json.dumps({
        "commit": OFFICIAL_COMMIT,
        "tag_reference": OFFICIAL_TAG,
        "archive_url": OFFICIAL_ARCHIVE,
        "archive_sha256": archive_hash,
    }, indent=2), encoding="utf-8")
    print(f"[OK] Official source pinned to commit: {OFFICIAL_COMMIT}")
    print(f"[OK] Source archive SHA-256: {archive_hash}")


def bootstrap_maven(tools: Path) -> Path:
    system = shutil.which("mvn.cmd") or shutil.which("mvn")
    if system:
        print(f"[OK] Maven found: {system}")
        return Path(system)

    maven_root = tools / f"apache-maven-{MAVEN_VERSION}"
    executable = maven_root / "bin" / ("mvn.cmd" if os.name == "nt" else "mvn")
    if executable.exists():
        print(f"[OK] Reusing isolated Maven {MAVEN_VERSION}: {executable}")
        return executable

    zip_path = tools / MAVEN_ZIP_NAME
    sha_path = tools / (MAVEN_ZIP_NAME + ".sha512")
    if not zip_path.exists():
        download(MAVEN_ZIP_URL, zip_path)
    if not sha_path.exists():
        download(MAVEN_SHA512_URL, sha_path)

    expected = sha_path.read_text(encoding="utf-8", errors="replace").strip().split()[0].lower()
    actual = hash_file(zip_path, "sha512").lower()
    if expected != actual:
        zip_path.unlink(missing_ok=True)
        raise RuntimeError(f"Apache Maven SHA-512 mismatch: expected {expected}, got {actual}")
    print(f"[OK] Apache Maven {MAVEN_VERSION} SHA-512 verified")

    if maven_root.exists():
        shutil.rmtree(maven_root)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tools)
    if not executable.exists():
        raise RuntimeError(f"Maven bootstrap completed but executable is missing: {executable}")
    return executable


def find_runtime_snapshot(ws: Path) -> Path:
    candidates = []
    expanded = ws / "expanded-community"
    if expanded.exists():
        for p in expanded.rglob("deck-downloader"):
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
        block = anchor + "\n" + '''        JButton btnDeckLibrary = new JButton("Descargar decks");
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
    tools = work / "tools"
    reports.mkdir(parents=True, exist_ok=True)
    tools.mkdir(parents=True, exist_ok=True)

    print("=== XMage Community Patch - PREPARE DECK DOWNLOADER PORT TO 1.4.61V1 ===")
    print("SAFE MODE: isolated source tree only.")
    print("Git is NOT required. Maven will be bootstrapped automatically if needed.\n")

    prepare_official_source(tools, source, reports)

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
    requirements.write_text(
        "requests\nbeautifulsoup4\nselenium\nundetected-chromedriver\nsetuptools\n",
        encoding="utf-8",
    )

    runtime_records = []
    for py in sorted(runtime_dst.glob("*.py")):
        py_compile.compile(str(py), doraise=True)
        runtime_records.append({"path": py.relative_to(source).as_posix(), "sha256": hash_file(py)})
    if not (runtime_dst / "deck_library_updater.py").exists():
        raise RuntimeError("deck_library_updater.py missing after runtime copy")
    print(f"[OK] Runtime Python syntax validated: {len(runtime_records)} files")

    assembly = source / "Mage.Client" / "src" / "main" / "assembly" / "distribution.xml"
    assembly_text = assembly.read_text(encoding="utf-8")
    if "<directory>release/</directory>" not in assembly_text:
        raise RuntimeError("Official client assembly no longer includes Mage.Client/release; packaging path unsafe")
    print("[OK] Official distribution includes Mage.Client/release runtime")

    mvn = bootstrap_maven(tools)
    env = os.environ.copy()
    build = run([mvn, "-pl", "Mage.Client", "-am", "-DskipTests", "package"], cwd=source, timeout=7200, env=env)
    (reports / "maven-build.log").write_text(build.stdout, encoding="utf-8")

    result = {
        "schema": 2,
        "official_tag": OFFICIAL_TAG,
        "official_commit": OFFICIAL_COMMIT,
        "source_method": "exact-commit-codeload-archive",
        "maven": str(mvn),
        "maven_version": MAVEN_VERSION,
        "runtime_files": runtime_records,
        "deck_downloader_source_sha256": hash_file(pane_dst),
        "mageframe_sha256": hash_file(mageframe),
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
        f"Official tag reference: {OFFICIAL_TAG}",
        f"Official commit pinned: {OFFICIAL_COMMIT}",
        "Source acquisition: exact GitHub commit archive (Git not required)",
        f"Maven executable: {mvn}",
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
