#!/usr/bin/env python3
"""Package and smoke-test the successfully compiled Deck Downloader V1 port.

This is the gate after prepare_deck_downloader_v1_port.py reports BUILD OK.
It never installs or activates XMage.

Checks:
- prior isolated Maven build is recorded as successful
- compiled Mage.Client JAR contains DeckDownloaderPane.class and MageFrame.class
- source runtime contains deck_library_updater.py and all Python files compile
- a Maven-produced client distribution ZIP exists
- the distribution ZIP actually contains the Deck Downloader runtime
- the distribution ZIP contains a client JAR with DeckDownloaderPane.class
- SHA-256 is generated for all selected candidate artifacts

Only if every mandatory check passes is a candidate ZIP copied to the
isolated candidate-output directory. Active XMage and clean V1 staging remain
untouched and V1 remains BLOCKED pending a manual GUI smoke test.
"""
from __future__ import annotations

import hashlib
import json
import py_compile
import shutil
import tempfile
import zipfile
from pathlib import Path

WORKSPACE = "migration-workspace"
PANE_CLASS = "mage/client/decks/DeckDownloaderPane.class"
FRAME_CLASS = "mage/client/MageFrame.class"
RUNTIME_SCRIPT = "config/deck-downloader/deck_library_updater.py"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(f"Missing required build result: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def jar_has(path: Path, entry: str) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            return entry in set(zf.namelist())
    except zipfile.BadZipFile:
        return False


def find_compiled_client_jar(source: Path) -> Path:
    candidates = []
    for p in (source / "Mage.Client" / "target").rglob("*.jar"):
        if jar_has(p, PANE_CLASS) and jar_has(p, FRAME_CLASS):
            candidates.append(p)
    if not candidates:
        raise RuntimeError("No compiled Mage.Client JAR contains DeckDownloaderPane.class + MageFrame.class")
    candidates.sort(key=lambda p: (p.stat().st_size, p.name), reverse=True)
    return candidates[0]


def normalize_zip_name(name: str) -> str:
    return name.replace("\\", "/").lstrip("./")


def zip_runtime_entries(zf: zipfile.ZipFile) -> list[str]:
    result = []
    for name in zf.namelist():
        n = normalize_zip_name(name).lower()
        if "/config/deck-downloader/" in "/" + n or n.startswith("config/deck-downloader/"):
            result.append(name)
    return result


def nested_client_jars_with_pane(zip_path: Path) -> list[str]:
    found = []
    with zipfile.ZipFile(zip_path) as outer:
        for info in outer.infolist():
            name = normalize_zip_name(info.filename)
            if not name.lower().endswith(".jar"):
                continue
            # Restrict to reasonably-sized nested JARs and inspect in memory/temp.
            with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                tmp.write(outer.read(info))
            try:
                if jar_has(tmp_path, PANE_CLASS) and jar_has(tmp_path, FRAME_CLASS):
                    found.append(name)
            finally:
                tmp_path.unlink(missing_ok=True)
    return found


def score_distribution(zip_path: Path) -> tuple[int, dict]:
    details = {"runtime_entries": [], "client_jars_with_pane": []}
    try:
        with zipfile.ZipFile(zip_path) as zf:
            details["runtime_entries"] = zip_runtime_entries(zf)
        details["client_jars_with_pane"] = nested_client_jars_with_pane(zip_path)
    except (zipfile.BadZipFile, OSError):
        return -1, details

    score = 0
    if any(normalize_zip_name(x).lower().endswith(RUNTIME_SCRIPT) for x in details["runtime_entries"]):
        score += 10
    if details["client_jars_with_pane"]:
        score += 20
    score += min(len(details["runtime_entries"]), 9)
    return score, details


def find_distribution(source: Path) -> tuple[Path, dict]:
    target = source / "Mage.Client" / "target"
    candidates = sorted(target.rglob("*.zip"))
    if not candidates:
        raise RuntimeError("Maven build produced no Mage.Client distribution ZIP")
    ranked = []
    for p in candidates:
        score, details = score_distribution(p)
        ranked.append((score, p.stat().st_size, p, details))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    score, _, best, details = ranked[0]
    if score < 30:
        raise RuntimeError(
            "No Maven-produced distribution ZIP contains BOTH Deck Downloader runtime "
            "and a client JAR with DeckDownloaderPane.class"
        )
    return best, details


def main() -> int:
    here = Path(__file__).resolve().parent
    ws = here / WORKSPACE
    work = ws / "port-1.4.61V1"
    source = work / "source"
    reports = work / "reports"
    output = work / "candidate-output"

    print("=== XMage Community Patch - V1 DECK DOWNLOADER PACKAGE/SMOKE GATE ===")
    print("SAFE MODE: validates isolated build only; nothing is installed.\n")

    build = load_json(reports / "port-build-result.json")
    if not build.get("build_ok") or build.get("build_returncode") != 0:
        raise RuntimeError("Previous isolated build is not recorded as successful")
    print("[OK] Previous Maven build recorded successful")

    client_jar = find_compiled_client_jar(source)
    print(f"[OK] Compiled client JAR contains DeckDownloaderPane + MageFrame: {client_jar}")

    runtime = source / "Mage.Client" / "release" / "config" / "deck-downloader"
    if not (runtime / "deck_library_updater.py").is_file():
        raise RuntimeError("Source runtime is missing deck_library_updater.py")
    py_files = sorted(runtime.glob("*.py"))
    if not py_files:
        raise RuntimeError("No Python runtime files found")
    for py in py_files:
        py_compile.compile(str(py), doraise=True)
    print(f"[OK] Runtime Python syntax: {len(py_files)} files")

    distribution, distribution_details = find_distribution(source)
    print(f"[OK] Maven distribution contains runtime + patched client JAR: {distribution}")
    print(f"[OK] Runtime entries in distribution: {len(distribution_details['runtime_entries'])}")
    print(f"[OK] Patched client JARs in distribution: {len(distribution_details['client_jars_with_pane'])}")

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    candidate = output / "XMage_1.4.61V1_CommunityPatch_DeckDownloader_SMOKE_CANDIDATE.zip"
    shutil.copy2(distribution, candidate)

    manifest = {
        "schema": 1,
        "status": "STATIC_SMOKE_PASSED_MANUAL_GUI_SMOKE_REQUIRED",
        "official_commit": build.get("official_commit"),
        "build_ok": True,
        "compiled_client_jar": str(client_jar),
        "compiled_client_jar_sha256": sha256(client_jar),
        "maven_distribution": str(distribution),
        "maven_distribution_sha256": sha256(distribution),
        "candidate_zip": str(candidate),
        "candidate_sha256": sha256(candidate),
        "runtime_python_files": [p.name for p in py_files],
        "distribution_runtime_entries": distribution_details["runtime_entries"],
        "distribution_client_jars_with_pane": distribution_details["client_jars_with_pane"],
        "active_xmage_modified": False,
        "clean_v1_staging_modified": False,
        "v1_activation_allowed": False,
    }
    (reports / "smoke-package-result.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    summary = [
        "XMage Community Patch - 1.4.61V1 STATIC SMOKE/PACKAGE RESULT",
        "===========================================================",
        "",
        "STATIC SMOKE: PASSED",
        f"Compiled DeckDownloaderPane present: YES",
        f"Runtime Python files validated: {len(py_files)}",
        "Runtime packaged in Maven distribution: YES",
        "Patched client JAR packaged in Maven distribution: YES",
        f"Candidate ZIP: {candidate}",
        f"Candidate SHA-256: {sha256(candidate)}",
        "",
        "IMPORTANT: this is NOT yet approved for activation.",
        "Next gate: manual isolated GUI launch/smoke test of client startup,",
        "Deck Downloader pane opening, runtime discovery and Cancel/Continue controls.",
        "",
        "Active XMage was NOT modified.",
        "Clean 1.4.61V1 staging was NOT modified.",
        "1.4.61V1 remains BLOCKED.",
    ]
    summary_path = reports / "RESUMEN_SMOKE_PACKAGE.txt"
    summary_path.write_text("\n".join(summary) + "\n", encoding="utf-8")

    print("\n=== STATIC SMOKE PASSED ===")
    print(f"Candidate: {candidate}")
    print(f"SHA-256: {sha256(candidate)}")
    print(f"Summary: {summary_path}")
    print("1.4.61V1 remains BLOCKED until manual isolated GUI smoke test.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("Active XMage was not modified. 1.4.61V1 remains BLOCKED.")
        input("Press Enter to close...")
        raise SystemExit(1)
