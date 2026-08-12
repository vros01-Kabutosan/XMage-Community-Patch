#!/usr/bin/env python3
"""Build and validate an isolated XMage 1.4.61V1 Deck Downloader candidate.

VERSION: V3
SAFE MODE: nothing is installed into active XMage.

Strategy:
1. Trust only the already-successful isolated Maven build record.
2. Verify the compiled client JAR really contains DeckDownloaderPane + MageFrame.
3. Generate the official Mage.Client assembly ZIP if needed.
4. Use that official assembly as the dependency/layout baseline.
5. In an isolated repair directory, replace its client JAR with the known-good
   compiled patched JAR and copy the validated runtime to config/deck-downloader.
6. Repack a Community Patch smoke candidate and validate it from the ZIP bytes.

This intentionally avoids relying on Maven's internal choice of project/local
repository artifact during assembly: the final candidate is deterministic and
its two community payloads are explicitly verified after repacking.
"""
from __future__ import annotations

import hashlib
import json
import py_compile
import shutil
import subprocess
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


def run(cmd, cwd: Path, log: Path, timeout=7200) -> None:
    print("$", " ".join(map(str, cmd)))
    proc = subprocess.run(
        [str(x) for x in cmd], cwd=cwd, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    log.write_text(proc.stdout or "", encoding="utf-8")
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout or "").splitlines()[-30:])
        raise RuntimeError(f"Maven command failed with code {proc.returncode}.\n{tail}")


def jar_has(path: Path, entry: str) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            return entry in set(zf.namelist())
    except (zipfile.BadZipFile, OSError):
        return False


def find_compiled_client_jar(source: Path) -> Path:
    candidates = [
        p for p in (source / "Mage.Client" / "target").glob("*.jar")
        if jar_has(p, PANE_CLASS) and jar_has(p, FRAME_CLASS)
    ]
    if not candidates:
        raise RuntimeError("No compiled Mage.Client JAR contains DeckDownloaderPane.class + MageFrame.class")
    return max(candidates, key=lambda p: (p.stat().st_size, p.name))


def find_or_generate_official_assembly(source: Path, reports: Path, build: dict) -> Path:
    target = source / "Mage.Client" / "target"
    zips = sorted(target.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if zips:
        print(f"[OK] Reusing existing Mage.Client assembly ZIP: {zips[0].name}")
        return zips[0]

    mvn = Path(str(build.get("maven", "")))
    if not mvn.exists():
        raise RuntimeError(f"Recorded Maven executable is missing: {mvn}")

    print("[STEP] Installing reactor artifacts for official assembly...")
    run([mvn, "-pl", "Mage.Client", "-am", "-DskipTests", "install"],
        source, reports / "maven-install-for-assembly.log")

    print("[STEP] Generating official Mage.Client assembly ZIP...")
    run([mvn, "-f", source / "Mage.Client" / "pom.xml", "-DskipTests", "assembly:single"],
        source, reports / "maven-client-assembly.log")

    zips = sorted(target.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not zips:
        raise RuntimeError("Official Mage.Client assembly did not produce any ZIP")
    print(f"[OK] Official assembly generated: {zips[0].name}")
    return zips[0]


def locate_client_jar_in_tree(root: Path) -> Path:
    candidates = []
    if (root / "lib").exists():
        candidates.extend((root / "lib").glob("mage-client*.jar"))
    if not candidates:
        candidates.extend(root.rglob("mage-client*.jar"))
    if not candidates:
        raise RuntimeError("Official assembly contains no mage-client JAR to replace")
    return max(candidates, key=lambda p: p.stat().st_size)


def create_repaired_candidate(assembly: Path, client_jar: Path, runtime: Path,
                              work: Path, output: Path) -> tuple[Path, dict]:
    repair = work / "candidate-repair-v3"
    if repair.exists():
        shutil.rmtree(repair)
    repair.mkdir(parents=True)

    print("[STEP] Extracting official assembly baseline...")
    with zipfile.ZipFile(assembly) as zf:
        zf.extractall(repair)

    packaged_client = locate_client_jar_in_tree(repair)
    old_hash = sha256(packaged_client)
    shutil.copy2(client_jar, packaged_client)
    new_hash = sha256(packaged_client)
    if new_hash != sha256(client_jar):
        raise RuntimeError("Patched client JAR copy verification failed")
    print(f"[OK] Replaced assembly client JAR: {packaged_client.relative_to(repair)}")

    runtime_dst = repair / "config" / "deck-downloader"
    if runtime_dst.exists():
        shutil.rmtree(runtime_dst)
    shutil.copytree(runtime, runtime_dst)
    print(f"[OK] Runtime injected: {runtime_dst.relative_to(repair)}")

    output.mkdir(parents=True, exist_ok=True)
    candidate = output / "XMage_1.4.61V1_CommunityPatch_DeckDownloader_SMOKE_CANDIDATE_V3.zip"
    candidate.unlink(missing_ok=True)
    print("[STEP] Repacking deterministic V3 smoke candidate...")
    with zipfile.ZipFile(candidate, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(repair.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(repair).as_posix())

    return candidate, {
        "official_assembly_client_sha256_before": old_hash,
        "candidate_client_sha256": new_hash,
        "candidate_client_path": packaged_client.relative_to(repair).as_posix(),
    }


def validate_candidate(candidate: Path) -> dict:
    runtime_entries = []
    client_hits = []
    with zipfile.ZipFile(candidate) as outer:
        names = outer.namelist()
        runtime_entries = [n for n in names if n.lower().startswith("config/deck-downloader/")]
        has_runtime_script = RUNTIME_SCRIPT in {n.lower() for n in names}

        for info in outer.infolist():
            if not info.filename.lower().endswith(".jar"):
                continue
            with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                tmp.write(outer.read(info))
            try:
                if jar_has(tmp_path, PANE_CLASS) and jar_has(tmp_path, FRAME_CLASS):
                    client_hits.append(info.filename)
            finally:
                tmp_path.unlink(missing_ok=True)

    if not has_runtime_script:
        raise RuntimeError("Final candidate ZIP is missing config/deck-downloader/deck_library_updater.py")
    if not client_hits:
        raise RuntimeError("Final candidate ZIP has no client JAR containing DeckDownloaderPane + MageFrame")

    return {
        "runtime_entries": runtime_entries,
        "client_jars_with_pane": client_hits,
        "has_runtime_script": True,
        "has_patched_client_jar": True,
    }


def main() -> int:
    here = Path(__file__).resolve().parent
    work = here / WORKSPACE / "port-1.4.61V1"
    source = work / "source"
    reports = work / "reports"
    output = work / "candidate-output-v3"

    print("=== XMage Community Patch - V1 DECK DOWNLOADER PACKAGE/SMOKE GATE V3 ===")
    print("SAFE MODE: isolated packaging only; active XMage is never touched.\n")

    build = load_json(reports / "port-build-result.json")
    if not build.get("build_ok") or build.get("build_returncode") != 0:
        raise RuntimeError("Previous isolated build is not recorded as successful")
    print("[OK] Previous Maven build recorded successful")

    client_jar = find_compiled_client_jar(source)
    print(f"[OK] Known-good patched client JAR: {client_jar}")

    runtime = source / "Mage.Client" / "release" / "config" / "deck-downloader"
    py_files = sorted(runtime.glob("*.py"))
    if not (runtime / "deck_library_updater.py").is_file() or not py_files:
        raise RuntimeError("Deck Downloader runtime is incomplete")
    for py in py_files:
        py_compile.compile(str(py), doraise=True)
    print(f"[OK] Runtime Python syntax: {len(py_files)} files")

    official_assembly = find_or_generate_official_assembly(source, reports, build)
    print(f"[OK] Official assembly baseline SHA-256: {sha256(official_assembly)}")

    if output.exists():
        shutil.rmtree(output)
    candidate, repair_meta = create_repaired_candidate(
        official_assembly, client_jar, runtime, work, output
    )

    validation = validate_candidate(candidate)
    candidate_hash = sha256(candidate)
    print(f"[OK] Final candidate runtime entries: {len(validation['runtime_entries'])}")
    print(f"[OK] Final candidate patched client JAR: {validation['client_jars_with_pane']}")
    print(f"[OK] Candidate SHA-256: {candidate_hash}")

    manifest = {
        "schema": 3,
        "tool_version": "V3",
        "status": "STATIC_SMOKE_PASSED_MANUAL_GUI_SMOKE_REQUIRED",
        "official_commit": build.get("official_commit"),
        "official_assembly": str(official_assembly),
        "official_assembly_sha256": sha256(official_assembly),
        "compiled_client_jar": str(client_jar),
        "compiled_client_jar_sha256": sha256(client_jar),
        "candidate_zip": str(candidate),
        "candidate_sha256": candidate_hash,
        "runtime_python_files": [p.name for p in py_files],
        **repair_meta,
        **validation,
        "active_xmage_modified": False,
        "clean_v1_staging_modified": False,
        "v1_activation_allowed": False,
    }
    (reports / "smoke-package-result-v3.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    summary = [
        "XMage Community Patch - 1.4.61V1 STATIC SMOKE/PACKAGE RESULT V3",
        "==============================================================",
        "",
        "STATIC SMOKE V3: PASSED",
        "Official XMage client assembly used as baseline: YES",
        "Known-good patched client JAR explicitly injected: YES",
        f"Runtime Python files validated/injected: {len(py_files)}",
        "Final candidate re-opened and verified from ZIP bytes: YES",
        f"Candidate ZIP: {candidate}",
        f"Candidate SHA-256: {candidate_hash}",
        "",
        "NEXT GATE: isolated GUI launch and manual Deck Downloader smoke test.",
        "Active XMage was NOT modified.",
        "Clean 1.4.61V1 staging was NOT modified.",
        "1.4.61V1 remains BLOCKED.",
    ]
    summary_path = reports / "RESUMEN_SMOKE_PACKAGE_V3.txt"
    summary_path.write_text("\n".join(summary) + "\n", encoding="utf-8")

    print("\n=== STATIC SMOKE V3 PASSED ===")
    print(f"Candidate: {candidate}")
    print(f"Summary: {summary_path}")
    print("1.4.61V1 remains BLOCKED until isolated GUI smoke test.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("Active XMage was not modified. 1.4.61V1 remains BLOCKED.")
        input("Press Enter to close...")
        raise SystemExit(1)
