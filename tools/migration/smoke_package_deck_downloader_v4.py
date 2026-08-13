#!/usr/bin/env python3
"""XMage 1.4.61V1 Deck Downloader smoke/package gate V4.

SAFE MODE: never modifies active XMage.

V4 fixes V3's bad assumption that the official assembly must already contain
an entry named mage-client*.jar. It identifies the client by bytecode content
(MageFrame.class). If the assembly omitted the project artifact entirely, V4
creates the exact official launcher target: lib/mage-client-1.4.61.jar.
"""
from __future__ import annotations

import json
import py_compile
import shutil
import zipfile
from pathlib import Path

import smoke_package_deck_downloader_v3 as base

VERSION = "V4"
EXPECTED_CLIENT_PATH = Path("lib") / "mage-client-1.4.61.jar"


def locate_or_create_client_slot(root: Path) -> tuple[Path, str, str | None]:
    jars = sorted(root.rglob("*.jar"))
    content_matches = [p for p in jars if base.jar_has(p, base.FRAME_CLASS)]
    if content_matches:
        chosen = max(content_matches, key=lambda p: p.stat().st_size)
        return chosen, "found_by_MageFrame_bytecode", base.sha256(chosen)

    target = root / EXPECTED_CLIENT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    return target, "created_exact_official_launcher_path", None


def create_candidate(assembly: Path, client_jar: Path, runtime: Path,
                     work: Path, output: Path) -> tuple[Path, dict]:
    repair = work / "candidate-repair-v4"
    if repair.exists():
        shutil.rmtree(repair)
    repair.mkdir(parents=True)

    print("[STEP] Extracting official assembly baseline...")
    with zipfile.ZipFile(assembly) as zf:
        zf.extractall(repair)

    packaged_client, detection, old_hash = locate_or_create_client_slot(repair)
    print(f"[INFO] Client slot method: {detection}")
    print(f"[INFO] Client slot: {packaged_client.relative_to(repair)}")

    shutil.copy2(client_jar, packaged_client)
    if base.sha256(packaged_client) != base.sha256(client_jar):
        raise RuntimeError("Patched client JAR copy verification failed")
    if not base.jar_has(packaged_client, base.PANE_CLASS) or not base.jar_has(packaged_client, base.FRAME_CLASS):
        raise RuntimeError("Injected client JAR does not contain DeckDownloaderPane + MageFrame")
    print("[OK] Patched client JAR injected and bytecode verified")

    runtime_dst = repair / "config" / "deck-downloader"
    if runtime_dst.exists():
        shutil.rmtree(runtime_dst)
    shutil.copytree(runtime, runtime_dst)
    if not (runtime_dst / "deck_library_updater.py").is_file():
        raise RuntimeError("Runtime injection failed")
    print("[OK] Deck Downloader runtime injected")

    output.mkdir(parents=True, exist_ok=True)
    candidate = output / "XMage_1.4.61V1_CommunityPatch_DeckDownloader_SMOKE_CANDIDATE_V4.zip"
    candidate.unlink(missing_ok=True)
    print("[STEP] Repacking V4 candidate...")
    with zipfile.ZipFile(candidate, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(repair.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(repair).as_posix())

    return candidate, {
        "client_slot_method": detection,
        "client_slot_path": packaged_client.relative_to(repair).as_posix(),
        "official_slot_sha256_before": old_hash,
        "candidate_client_sha256": base.sha256(packaged_client),
    }


def main() -> int:
    here = Path(__file__).resolve().parent
    work = here / base.WORKSPACE / "port-1.4.61V1"
    source = work / "source"
    reports = work / "reports"
    output = work / "candidate-output-v4"

    print("=== XMage Community Patch - V1 DECK DOWNLOADER PACKAGE/SMOKE GATE V4 ===")
    print("SAFE MODE: isolated packaging only; active XMage is never touched.\n")

    build = base.load_json(reports / "port-build-result.json")
    if not build.get("build_ok") or build.get("build_returncode") != 0:
        raise RuntimeError("Previous isolated build is not recorded as successful")
    print("[OK] Previous Maven build recorded successful")

    client_jar = base.find_compiled_client_jar(source)
    print(f"[OK] Known-good patched client JAR: {client_jar}")

    runtime = source / "Mage.Client" / "release" / "config" / "deck-downloader"
    py_files = sorted(runtime.glob("*.py"))
    if not (runtime / "deck_library_updater.py").is_file() or not py_files:
        raise RuntimeError("Deck Downloader runtime is incomplete")
    for py in py_files:
        py_compile.compile(str(py), doraise=True)
    print(f"[OK] Runtime Python syntax: {len(py_files)} files")

    assembly = base.find_or_generate_official_assembly(source, reports, build)
    print(f"[OK] Official assembly baseline SHA-256: {base.sha256(assembly)}")

    if output.exists():
        shutil.rmtree(output)
    candidate, slot_meta = create_candidate(assembly, client_jar, runtime, work, output)

    validation = base.validate_candidate(candidate)
    candidate_hash = base.sha256(candidate)
    expected_entry = EXPECTED_CLIENT_PATH.as_posix()
    with zipfile.ZipFile(candidate) as zf:
        names = set(zf.namelist())
    if expected_entry not in names and slot_meta["client_slot_method"] == "created_exact_official_launcher_path":
        raise RuntimeError(f"Final candidate missing official launcher target {expected_entry}")

    print(f"[OK] Final candidate runtime entries: {len(validation['runtime_entries'])}")
    print(f"[OK] Final candidate patched client JAR: {validation['client_jars_with_pane']}")
    print(f"[OK] Candidate SHA-256: {candidate_hash}")

    manifest = {
        "schema": 4,
        "tool_version": VERSION,
        "status": "STATIC_SMOKE_PASSED_MANUAL_GUI_SMOKE_REQUIRED",
        "official_commit": build.get("official_commit"),
        "official_assembly": str(assembly),
        "official_assembly_sha256": base.sha256(assembly),
        "compiled_client_jar": str(client_jar),
        "compiled_client_jar_sha256": base.sha256(client_jar),
        "candidate_zip": str(candidate),
        "candidate_sha256": candidate_hash,
        "runtime_python_files": [p.name for p in py_files],
        **slot_meta,
        **validation,
        "active_xmage_modified": False,
        "clean_v1_staging_modified": False,
        "v1_activation_allowed": False,
    }
    (reports / "smoke-package-result-v4.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    summary = reports / "RESUMEN_SMOKE_PACKAGE_V4.txt"
    summary.write_text(
        "XMage Community Patch - 1.4.61V1 STATIC SMOKE/PACKAGE RESULT V4\n"
        "==============================================================\n\n"
        "STATIC SMOKE V4: PASSED\n"
        f"Client slot method: {slot_meta['client_slot_method']}\n"
        f"Client slot path: {slot_meta['client_slot_path']}\n"
        f"Runtime Python files validated/injected: {len(py_files)}\n"
        "Final candidate re-opened and verified from ZIP bytes: YES\n"
        f"Candidate ZIP: {candidate}\n"
        f"Candidate SHA-256: {candidate_hash}\n\n"
        "NEXT GATE: isolated GUI launch and manual Deck Downloader smoke test.\n"
        "Active XMage was NOT modified.\n"
        "1.4.61V1 remains BLOCKED.\n",
        encoding="utf-8",
    )

    print("\n=== STATIC SMOKE V4 PASSED ===")
    print(f"Candidate: {candidate}")
    print(f"Summary: {summary}")
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
