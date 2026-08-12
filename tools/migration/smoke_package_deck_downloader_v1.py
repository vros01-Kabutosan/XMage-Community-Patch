#!/usr/bin/env python3
"""Package and smoke-test the successfully compiled Deck Downloader V1 port.

SAFE MODE: isolated build only. Never installs or activates XMage.

Important XMage detail: Mage.Client configures maven-assembly-plugin, but the
assembly goal is not bound to the normal package lifecycle. Therefore a plain
`mvn ... package` correctly builds mage-client-1.4.61.jar but does not create
the client distribution ZIP. This gate explicitly generates the official
assembly when it is missing, then validates its contents.
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
        tail = "\n".join((proc.stdout or "").splitlines()[-20:])
        raise RuntimeError(f"Maven command failed with code {proc.returncode}.\n{tail}")


def jar_has(path: Path, entry: str) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            return entry in set(zf.namelist())
    except (zipfile.BadZipFile, OSError):
        return False


def find_compiled_client_jar(source: Path) -> Path:
    candidates = [
        p for p in (source / "Mage.Client" / "target").rglob("*.jar")
        if jar_has(p, PANE_CLASS) and jar_has(p, FRAME_CLASS)
    ]
    if not candidates:
        raise RuntimeError("No compiled Mage.Client JAR contains DeckDownloaderPane.class + MageFrame.class")
    return max(candidates, key=lambda p: (p.stat().st_size, p.name))


def normalize(name: str) -> str:
    return name.replace("\\", "/").lstrip("./")


def zip_runtime_entries(zf: zipfile.ZipFile) -> list[str]:
    return [
        name for name in zf.namelist()
        if normalize(name).lower().startswith("config/deck-downloader/")
    ]


def nested_client_jars_with_pane(zip_path: Path) -> list[str]:
    found = []
    with zipfile.ZipFile(zip_path) as outer:
        for info in outer.infolist():
            name = normalize(info.filename)
            if not name.lower().endswith(".jar"):
                continue
            with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                tmp.write(outer.read(info))
            try:
                if jar_has(tmp_path, PANE_CLASS) and jar_has(tmp_path, FRAME_CLASS):
                    found.append(name)
            finally:
                tmp_path.unlink(missing_ok=True)
    return found


def inspect_distribution(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as zf:
        runtime = zip_runtime_entries(zf)
    jars = nested_client_jars_with_pane(zip_path)
    return {
        "runtime_entries": runtime,
        "client_jars_with_pane": jars,
        "has_runtime_script": any(normalize(x).lower().endswith(RUNTIME_SCRIPT) for x in runtime),
        "has_patched_client_jar": bool(jars),
    }


def valid_distributions(source: Path) -> list[tuple[Path, dict]]:
    result = []
    for p in sorted((source / "Mage.Client" / "target").glob("*.zip")):
        try:
            details = inspect_distribution(p)
        except (zipfile.BadZipFile, OSError):
            continue
        if details["has_runtime_script"] and details["has_patched_client_jar"]:
            result.append((p, details))
    return result


def ensure_distribution(source: Path, reports: Path, build: dict) -> tuple[Path, dict, bool]:
    existing = valid_distributions(source)
    if existing:
        p, d = max(existing, key=lambda x: x[0].stat().st_size)
        return p, d, False

    mvn = Path(str(build.get("maven", "")))
    if not mvn.exists():
        raise RuntimeError(f"Recorded Maven executable is missing: {mvn}")

    print("[INFO] No distribution ZIP yet. XMage assembly is not bound to package.")
    print("[STEP] Installing reactor artifacts needed by Mage.Client assembly...")
    run(
        [mvn, "-pl", "Mage.Client", "-am", "-DskipTests", "install"],
        source,
        reports / "maven-install-for-assembly.log",
    )

    print("[STEP] Generating official Mage.Client distribution with assembly:single...")
    run(
        [mvn, "-f", source / "Mage.Client" / "pom.xml", "-DskipTests", "assembly:single"],
        source,
        reports / "maven-client-assembly.log",
    )

    generated = valid_distributions(source)
    if not generated:
        raise RuntimeError(
            "Official assembly completed but no ZIP contains both the Deck Downloader runtime "
            "and the patched Mage.Client JAR"
        )
    p, d = max(generated, key=lambda x: x[0].stat().st_size)
    return p, d, True


def main() -> int:
    here = Path(__file__).resolve().parent
    work = here / WORKSPACE / "port-1.4.61V1"
    source = work / "source"
    reports = work / "reports"
    output = work / "candidate-output"

    print("=== XMage Community Patch - V1 DECK DOWNLOADER PACKAGE/SMOKE GATE v2 ===")
    print("SAFE MODE: validates/generates artifacts in isolated workspace only.\n")

    build = load_json(reports / "port-build-result.json")
    if not build.get("build_ok") or build.get("build_returncode") != 0:
        raise RuntimeError("Previous isolated build is not recorded as successful")
    print("[OK] Previous Maven build recorded successful")

    client_jar = find_compiled_client_jar(source)
    print(f"[OK] Compiled client JAR contains DeckDownloaderPane + MageFrame: {client_jar}")

    runtime = source / "Mage.Client" / "release" / "config" / "deck-downloader"
    py_files = sorted(runtime.glob("*.py"))
    if not (runtime / "deck_library_updater.py").is_file() or not py_files:
        raise RuntimeError("Deck Downloader runtime is incomplete")
    for py in py_files:
        py_compile.compile(str(py), doraise=True)
    print(f"[OK] Runtime Python syntax: {len(py_files)} files")

    distribution, details, generated_now = ensure_distribution(source, reports, build)
    print(f"[OK] Distribution ZIP: {distribution}")
    print(f"[OK] Runtime entries packaged: {len(details['runtime_entries'])}")
    print(f"[OK] Patched client JAR packaged: {details['client_jars_with_pane']}")

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    candidate = output / "XMage_1.4.61V1_CommunityPatch_DeckDownloader_SMOKE_CANDIDATE.zip"
    shutil.copy2(distribution, candidate)
    candidate_hash = sha256(candidate)

    manifest = {
        "schema": 2,
        "status": "STATIC_SMOKE_PASSED_MANUAL_GUI_SMOKE_REQUIRED",
        "official_commit": build.get("official_commit"),
        "assembly_generated_by_gate": generated_now,
        "compiled_client_jar": str(client_jar),
        "compiled_client_jar_sha256": sha256(client_jar),
        "maven_distribution": str(distribution),
        "maven_distribution_sha256": sha256(distribution),
        "candidate_zip": str(candidate),
        "candidate_sha256": candidate_hash,
        "runtime_python_files": [p.name for p in py_files],
        "distribution_runtime_entries": details["runtime_entries"],
        "distribution_client_jars_with_pane": details["client_jars_with_pane"],
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
        "Compiled DeckDownloaderPane present: YES",
        f"Runtime Python files validated: {len(py_files)}",
        "Runtime packaged in official Mage.Client assembly: YES",
        "Patched client JAR packaged in official Mage.Client assembly: YES",
        f"Assembly generated during this gate: {generated_now}",
        f"Candidate ZIP: {candidate}",
        f"Candidate SHA-256: {candidate_hash}",
        "",
        "NEXT GATE: isolated GUI launch and manual Deck Downloader smoke test.",
        "Active XMage was NOT modified.",
        "Clean V1 staging was NOT modified.",
        "1.4.61V1 remains BLOCKED.",
    ]
    summary_path = reports / "RESUMEN_SMOKE_PACKAGE.txt"
    summary_path.write_text("\n".join(summary) + "\n", encoding="utf-8")

    print("\n=== STATIC SMOKE PASSED ===")
    print(f"Candidate: {candidate}")
    print(f"SHA-256: {candidate_hash}")
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
