#!/usr/bin/env python3
"""XMage Community Patch - three-way reconstructed Java source comparator.

Compares NON-CARD Java using the SAME decompiler (verified CFR 0.152):
  official 1.4.60V3  <->  Community RC1  <->  official 1.4.61V1

Why same-decompiler comparison:
Comparing original Java source with decompiled RC1 Java introduces formatting and
compiler-reconstruction noise. This tool decompiles all three binary generations
with the same CFR version/settings, then compares normalized Java text.

Classifications:
- NO_ACTION: V3 == RC1 == V1
- UPSTREAM_ALREADY_HAS: RC1 == V1 != V3
- PORT_COMMUNITY_CHANGE: V3 == V1 != RC1
- REAL_CONFLICT: V3, RC1, V1 all materially differ
- REVIEW_REQUIRED: structural/missing/ambiguous case

SAFE MODE:
- reads only migration-workspace
- writes reports under migration-workspace/reports
- never modifies active XMage
- never modifies 1.4.61V1 staging
- never copies RC1 JARs over target
"""

from __future__ import annotations

import csv
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

WORKSPACE_NAME = "migration-workspace"
JAR_VERSION_RE = re.compile(r"-1\.4\.60(?=\.jar$)", re.IGNORECASE)
CFR_VERSION = "0.152"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(f"Missing required input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


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
            if logical:
                out[logical] = p
    return out


def target_candidate(logical_v3: str, v1_index: dict[str, Path]) -> tuple[str | None, Path | None]:
    if logical_v3 in v1_index:
        return logical_v3, v1_index[logical_v3]
    upgraded = JAR_VERSION_RE.sub("-1.4.61", logical_v3)
    if upgraded in v1_index:
        return upgraded, v1_index[upgraded]
    basename = Path(upgraded).name.lower()
    matches = [(k, v) for k, v in v1_index.items() if Path(k).name.lower() == basename]
    if len(matches) == 1:
        return matches[0]
    return None, None


def normalize_java(text: str) -> str:
    """Normalize CFR output while preserving Java tokens and literals.

    CFR is invoked with comments disabled, so the main remaining non-semantic
    noise is line ending/indentation/trailing whitespace. We intentionally do
    NOT rename variables or reorder constructs: those can carry real evidence.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    # Trim outer blank lines and collapse runs of blank lines.
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    out = []
    blank = False
    for line in lines:
        if not line.strip():
            if not blank:
                out.append("")
            blank = True
        else:
            # CFR indentation is deterministic for same bytecode structure;
            # normalize tabs only.
            out.append(line.replace("\t", "    "))
            blank = False
    return "\n".join(out) + "\n"


def text_hash(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    return hashlib.sha256(normalize_java(text).encode("utf-8")).hexdigest()


def classify(h3: str | None, hrc1: str | None, h1: str | None) -> str:
    if h3 is not None and hrc1 is not None and h1 is not None:
        if h3 == hrc1 == h1:
            return "NO_ACTION"
        if hrc1 == h1 and h3 != hrc1:
            return "UPSTREAM_ALREADY_HAS"
        if h3 == h1 and hrc1 != h3:
            return "PORT_COMMUNITY_CHANGE"
        if len({h3, hrc1, h1}) == 3:
            return "REAL_CONFLICT"
        return "REVIEW_REQUIRED"

    # Structural cases.
    if h3 is None and hrc1 is not None and h1 is not None:
        return "UPSTREAM_ALREADY_HAS" if hrc1 == h1 else "REVIEW_REQUIRED"
    if h3 is not None and hrc1 is None and h1 is None:
        return "UPSTREAM_ALREADY_HAS"  # community removal also removed upstream
    if h3 is not None and hrc1 is not None and h1 is None:
        return "REAL_CONFLICT"  # community kept/changed, target removed
    if h3 is None and hrc1 is not None and h1 is None:
        return "PORT_COMMUNITY_CHANGE"  # community-only addition
    if h3 is not None and hrc1 is None and h1 is not None:
        return "REAL_CONFLICT"  # community removed but target kept
    return "REVIEW_REQUIRED"


def safe_name(source: str) -> str:
    return source.replace("/", "__").replace("\\", "__").replace(":", "_")


def write_diff(path: Path, a: Path | None, b: Path | None, a_label: str, b_label: str) -> None:
    at = normalize_java(a.read_text(encoding="utf-8", errors="replace")) if a and a.exists() else ""
    bt = normalize_java(b.read_text(encoding="utf-8", errors="replace")) if b and b.exists() else ""
    diff = difflib.unified_diff(
        at.splitlines(keepends=True), bt.splitlines(keepends=True),
        fromfile=a_label, tofile=b_label, n=5,
    )
    path.write_text("".join(diff), encoding="utf-8")


def decompile_jar(cfr: Path, jar: Path, dest: Path) -> None:
    marker = dest / ".decompile-ok.json"
    fingerprint = {"jar_sha256": sha256_file(jar), "cfr": CFR_VERSION}
    if marker.exists():
        try:
            old = json.loads(marker.read_text(encoding="utf-8"))
            if old == fingerprint:
                return
        except Exception:
            pass
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["java", "-jar", str(cfr), str(jar), "--outputdir", str(dest), "--silent", "true", "--comments", "false"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1200,
    )
    (dest / "cfr.log").write_text(proc.stdout or "", encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"CFR failed for {jar}; see {dest / 'cfr.log'}")
    marker.write_text(json.dumps(fingerprint, indent=2), encoding="utf-8")


def main() -> int:
    here = Path(__file__).resolve().parent
    ws = here / WORKSPACE_NAME
    recon_root = ws / "reports" / "migration-analysis" / "source-reconstruction"
    recon_json = load_json(recon_root / "reconstruction.json")
    class_json = load_json(ws / "reports" / "migration-analysis" / "bytecode-analysis" / "noncard-classification" / "noncard-source-classification.json")

    cfr = recon_root / "tools" / f"cfr-{CFR_VERSION}.jar"
    if not cfr.exists():
        raise RuntimeError("Verified CFR tool is missing. Run RUN_RECONSTRUCT_RC1_SOURCES_WINDOWS.cmd first.")

    v3_index = file_index(ws / "extracted" / "upstream-v3")
    v1_index = file_index(ws / "staging" / "xmage_1.4.61V1-clean")

    print("=== XMage Community Patch - THREE-WAY RECONSTRUCTED SOURCE COMPARE ===")
    print("SAFE MODE: reports only; active XMage and staging are not modified.\n")

    # Build source metadata from classification and reconstruction.
    class_by_source = {r.get("probable_source"): r for r in class_json.get("sources", [])}
    recon_by_source = {r.get("source"): r for r in recon_json.get("records", [])}
    sources = sorted(set(class_by_source) & set(recon_by_source), key=str.lower)
    if not sources:
        raise RuntimeError("No reconstructed/classified source intersection found")

    # Determine unique official JAR pairs needed.
    jar_pairs: dict[str, tuple[Path, str, Path]] = {}
    unresolved_jars = []
    for source in sources:
        logical = recon_by_source[source].get("jar", "")
        v3 = v3_index.get(logical)
        target_logical, v1 = target_candidate(logical, v1_index)
        if not v3 or not v1 or not target_logical:
            unresolved_jars.append({"source": source, "rc1_jar": logical})
            continue
        jar_pairs[logical] = (v3, target_logical, v1)

    decomp_root = recon_root / "official-threeway-decompiled"
    v3_root = decomp_root / "v3"
    v1_root = decomp_root / "v1"
    v3_root.mkdir(parents=True, exist_ok=True)
    v1_root.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Non-card sources: {len(sources)}")
    print(f"[INFO] Unique official JAR pairs: {len(jar_pairs)}")

    jar_dirs = {}
    for i, (logical, (v3, target_logical, v1)) in enumerate(sorted(jar_pairs.items()), start=1):
        key = f"{i:02d}_{Path(logical).stem}"
        d3 = v3_root / key
        d1 = v1_root / key
        print(f"[{i}/{len(jar_pairs)}] V3/V1 CFR: {logical} -> {target_logical}")
        decompile_jar(cfr, v3, d3)
        decompile_jar(cfr, v1, d1)
        jar_dirs[logical] = (d3, d1, target_logical)

    out = ws / "reports" / "migration-analysis" / "source-threeway"
    diffs = out / "diffs"
    if diffs.exists():
        shutil.rmtree(diffs)
    diffs.mkdir(parents=True, exist_ok=True)

    rows = []
    missing = []
    rc1_selected = recon_root / "selected-noncard-sources"

    for source in sources:
        meta = class_by_source[source]
        rec = recon_by_source[source]
        logical = rec.get("jar", "")
        java_entry = meta.get("java_entry", "")
        if logical not in jar_dirs:
            missing.append({"source": source, "reason": "official jar mapping unavailable"})
            continue
        d3, d1, target_logical = jar_dirs[logical]

        p3 = d3 / java_entry
        p1 = d1 / java_entry
        pr = rc1_selected / source
        # CFR may occasionally place a uniquely-named source differently.
        if not p3.exists():
            m = list(d3.rglob(Path(java_entry).name))
            if len(m) == 1:
                p3 = m[0]
        if not p1.exists():
            m = list(d1.rglob(Path(java_entry).name))
            if len(m) == 1:
                p1 = m[0]

        h3, hr, h1 = text_hash(p3), text_hash(pr), text_hash(p1)
        action = classify(h3, hr, h1)
        row = {
            "action": action,
            "subsystem": meta.get("subsystem", "unknown"),
            "source": source,
            "java_entry": java_entry,
            "rc1_jar": logical,
            "target_jar": target_logical,
            "v3_exists": bool(p3.exists()),
            "rc1_exists": bool(pr.exists()),
            "v1_exists": bool(p1.exists()),
            "v3_hash": h3 or "",
            "rc1_hash": hr or "",
            "v1_hash": h1 or "",
            "previous_hash_classifier": meta.get("action", ""),
        }
        rows.append(row)

        if action not in {"NO_ACTION", "UPSTREAM_ALREADY_HAS"}:
            stem = safe_name(source)
            write_diff(diffs / f"{stem}.V3_to_RC1.diff", p3 if p3.exists() else None, pr if pr.exists() else None, "official-1.4.60V3", "community-RC1")
            write_diff(diffs / f"{stem}.V3_to_V1.diff", p3 if p3.exists() else None, p1 if p1.exists() else None, "official-1.4.60V3", "official-1.4.61V1")
            write_diff(diffs / f"{stem}.RC1_to_V1.diff", pr if pr.exists() else None, p1 if p1.exists() else None, "community-RC1", "official-1.4.61V1")

    order = {"REAL_CONFLICT": 0, "PORT_COMMUNITY_CHANGE": 1, "REVIEW_REQUIRED": 2, "UPSTREAM_ALREADY_HAS": 3, "NO_ACTION": 4}
    rows.sort(key=lambda r: (order.get(r["action"], 9), r["subsystem"], r["source"].lower()))

    out.mkdir(parents=True, exist_ok=True)
    fields = ["action", "subsystem", "source", "java_entry", "rc1_jar", "target_jar", "v3_exists", "rc1_exists", "v1_exists", "v3_hash", "rc1_hash", "v1_hash", "previous_hash_classifier"]
    with (out / "SOURCE_THREEWAY_CLASSIFICATION.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    counts = Counter(r["action"] for r in rows)
    machine = {
        "schema": 1,
        "method": "same-CFR-0.152-three-way-reconstructed-Java",
        "counts": dict(counts),
        "sources_compared": len(rows),
        "unresolved": unresolved_jars + missing,
        "rows": rows,
    }
    (out / "source-threeway.json").write_text(json.dumps(machine, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "XMage Community Patch - THREE-WAY RECONSTRUCTED SOURCE RESULT",
        "============================================================",
        "",
        "Method: same CFR 0.152 for official V3 / Community RC1 / official V1",
        "SAFE MODE: active XMage and 1.4.61V1 staging were not modified.",
        "",
        f"Sources compared: {len(rows)}",
        f"Unresolved mappings: {len(unresolved_jars) + len(missing)}",
        "",
        "SOURCE COUNTS",
    ]
    for a in ("REAL_CONFLICT", "PORT_COMMUNITY_CHANGE", "REVIEW_REQUIRED", "UPSTREAM_ALREADY_HAS", "NO_ACTION"):
        lines.append(f"{a}: {counts.get(a, 0)}")
    lines += ["", "ACTION LIST"]
    for r in rows:
        lines.append(f"[{r['action']}] [{r['subsystem']}] {r['source']}")
    if unresolved_jars or missing:
        lines += ["", "UNRESOLVED"]
        for x in unresolved_jars + missing:
            lines.append(json.dumps(x, ensure_ascii=False))
    lines += [
        "",
        "SAFETY GATE",
        "1.4.61V1 remains BLOCKED.",
        "NO_ACTION and UPSTREAM_ALREADY_HAS receive no RC1 patch.",
        "PORT_COMMUNITY_CHANGE can become a reproducible RC1 source patch after manual diff verification.",
        "REAL_CONFLICT and REVIEW_REQUIRED require explicit merge against 1.4.61V1 source.",
    ]
    (out / "RESUMEN_SOURCE_THREEWAY.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n=== COMPLETE ===")
    for a in ("REAL_CONFLICT", "PORT_COMMUNITY_CHANGE", "REVIEW_REQUIRED", "UPSTREAM_ALREADY_HAS", "NO_ACTION"):
        print(f"{a}: {counts.get(a, 0)}")
    print(f"Unresolved: {len(unresolved_jars) + len(missing)}")
    print(f"Summary: {out / 'RESUMEN_SOURCE_THREEWAY.txt'}")
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
