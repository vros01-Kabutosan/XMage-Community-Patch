#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import json, hashlib, shutil, subprocess, time, re

HERE = Path(__file__).resolve().parent
WORK = HERE / "migration-workspace"
PORT = WORK / "port-1.4.61V1"
SRC = PORT / "source"

GAME = SRC / "Mage.Client" / "src" / "main" / "java" / "mage" / "client" / "game" / "GamePanel.java"
HAND = SRC / "Mage.Client" / "src" / "main" / "java" / "mage" / "client" / "game" / "HandPanel.java"
CARDS = SRC / "Mage.Client" / "src" / "main" / "java" / "mage" / "client" / "cards" / "Cards.java"
DRAG = SRC / "Mage.Client" / "src" / "main" / "java" / "mage" / "client" / "cards" / "DragCardGrid.java"
CARD_INFO = SRC / "Mage.Client" / "src" / "main" / "java" / "org" / "mage" / "plugins" / "card" / "info" / "CardInfoPaneImpl.java"
MANA = SRC / "Mage.Client" / "src" / "main" / "java" / "org" / "mage" / "card" / "arcane" / "ManaSymbols.java"

MAVEN = PORT / "tools" / "apache-maven-3.9.16" / "bin" / "mvn.cmd"

OUT = WORK / "xmage-v4-ux-final-r5"
REPORT = OUT / "XMAGE_V4_UX_FINAL_R5.json"
SUMMARY = OUT / "RESUMEN_XMAGE_V4_UX_FINAL_R5.txt"
BUILD_LOG = OUT / "XMAGE_V4_UX_FINAL_R5_BUILD.log"
SMOKE_LOG = OUT / "XMAGE_V4_UX_FINAL_R5_STATIC_SMOKE.txt"

ACTIVE_JAR = Path(r"J:\MTG\xmage\mage-client\lib\mage-client-1.4.61.jar")

def need(cond, msg):
    if not cond:
        raise RuntimeError(msg)

def read(path):
    need(path.is_file(), f"Missing file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")

def write(path, text):
    path.write_text(text, encoding="utf-8")

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def patch_imports(text):
    changed = False

    # R4 added Dimension and Toolkit usage in CardInfoPaneImpl. Upstream only had Component.
    needed_imports = [
        "import java.awt.Dimension;",
        "import java.awt.Toolkit;",
    ]

    if "import java.awt.Component;" in text:
        for imp in needed_imports:
            if imp not in text:
                text = text.replace("import java.awt.Component;\n", "import java.awt.Component;\n" + imp + "\n", 1)
                changed = True
    else:
        raise RuntimeError("CardInfoPaneImpl import anchor not found")

    # Keep the file clean if a bad manual attempt duplicated imports.
    for imp in needed_imports:
        text = re.sub(r"(?m)^" + re.escape(imp) + r"\n(?:\s*" + re.escape(imp) + r"\n)+", imp + "\n", text)

    return text, changed

def validate_expected_source():
    checks = {
        "board_layout_v3_v4": "XCP_BOARD_LAYOUT_POLISH_V3_V4" in read(GAME),
        "stack_polish_v3_v4": "XCP_FLOATING_STACK_POLISH_V3_V4_START" in read(GAME),
        "stack_bottom_resize_r4": "XCP_STACK_BOTTOM_RESIZE_V4_R4" in read(GAME),
        "hand_scale_v3_v4": "XCP_HAND_SCALE_V3_V4_START" in read(HAND),
        "stack_order_v4": "XCP_STACK_RESOLUTION_ORDER_V4" in read(CARDS),
        "selector_v6": "XCP_PRINTING_SELECTOR_V6_EXACT_OLD" in read(DRAG),
        "tooltip_r2": "XCP_CARD_INFO_CONTEXT_POLISH_V3_V4_R2" in read(CARD_INFO),
        "tooltip_r4": "XCP_CONTEXT_TOOLTIP_FINAL_V4_R4" in read(CARD_INFO),
        "set_symbol_r4": "XCP_SET_SYMBOL_DIRECT_FALLBACK_V4_R4" in read(MANA),
    }
    failed = [k for k, v in checks.items() if not v]
    need(not failed, "Expected V4/R4 source is incomplete: " + ", ".join(failed))
    return checks

def run_build():
    mvn = str(MAVEN) if MAVEN.is_file() else "mvn"
    return subprocess.run(
        [mvn, "-pl", "Mage.Client", "-am", "-DskipTests", "package"],
        cwd=str(SRC),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

def locate_javap():
    for exe in ("javap.exe", "javap"):
        p = shutil.which(exe)
        if p:
            return p
    for p in (
        Path(r"C:\Program Files\BellSoft\LibericaJDK-17\bin\javap.exe"),
        Path(r"C:\Program Files\Java\jdk-17\bin\javap.exe"),
        Path(r"J:\MTG\java\bin\javap.exe"),
    ):
        if p.is_file():
            return str(p)
    return None

def javap_dump(javap, jar, cls):
    cp = subprocess.run(
        [javap, "-classpath", str(jar), "-p", "-c", "-constants", cls],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120
    )
    need(cp.returncode == 0, f"javap failed for {cls}")
    return cp.stdout

def static_smoke(candidate):
    javap = locate_javap()
    need(javap, "javap not found")

    dumps = {
        "GamePanel": javap_dump(javap, candidate, "mage.client.game.GamePanel"),
        "HandPanel": javap_dump(javap, candidate, "mage.client.game.HandPanel"),
        "Cards": javap_dump(javap, candidate, "mage.client.cards.Cards"),
        "DragCardGrid": javap_dump(javap, candidate, "mage.client.cards.DragCardGrid"),
        "CardInfoPaneImpl": javap_dump(javap, candidate, "org.mage.plugins.card.info.CardInfoPaneImpl"),
        "ManaSymbols": javap_dump(javap, candidate, "org.mage.card.arcane.ManaSymbols"),
    }

    checks = {
        "bottom_resize_active": (
    "getLocationOnScreen" in dumps["GamePanel"]
    and "getSize" in dumps["GamePanel"]
    and "setSize" in dumps["GamePanel"]
    and "saveFloatingStackBounds" in dumps["GamePanel"]
),
        "stack_bounds_persistence": "saveFloatingStackBounds" in dumps["GamePanel"],
        "hand_scale": "getCommunityHandCardDimension" in dumps["HandPanel"],
        "stack_order_no_reverse": "java/util/Collections.reverse" not in dumps["Cards"],
        "selector_v6": "chooseEdition" in dumps["DragCardGrid"] and "ImageCache.getCardImage" in dumps["DragCardGrid"],
        "tooltip_real_measure": "getPreferredSize" in dumps["CardInfoPaneImpl"],
        "tooltip_screen_fit": "keepComponentInsideScreen" in dumps["CardInfoPaneImpl"],
        "set_symbol_small_large": "ResourceSetSize.SMALL" in dumps["ManaSymbols"] and "ResourceSetSize.LARGE" in dumps["ManaSymbols"],
        "set_symbol_file_icon": "filePathToUrl" in dumps["ManaSymbols"],
    }

    failed = [k for k, v in checks.items() if not v]
    SMOKE_LOG.write_text(
        "\n".join(["XMage Community Patch - V4 UX FINAL R5 STATIC SMOKE", ""]
                  + [f"{k}: {'PASS' if v else 'FAIL'}" for k, v in checks.items()]),
        encoding="utf-8"
    )
    need(not failed, "Static Smoke failed: " + ", ".join(failed))
    return checks

def powershell(script):
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45
    )

def get_xmage_processes():
    ps = r'''
$procs = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -ieq 'java.exe' -or $_.Name -ieq 'javaw.exe') -and
    $_.CommandLine -and (
        $_.CommandLine.ToLower().Contains('j:\mtg\xmage') -or
        $_.CommandLine.ToLower().Contains('xmagelauncher') -or
        $_.CommandLine.ToLower().Contains('mage.server.main') -or
        $_.CommandLine.ToLower().Contains('mage.client')
    )
}
$procs | ForEach-Object {
    Write-Output ("PID=" + $_.ProcessId + "|" + $_.Name + "|" + $_.CommandLine)
}
'''
    cp = powershell(ps)
    return [x.strip() for x in cp.stdout.splitlines() if x.strip().startswith("PID=")]

def close_xmage():
    ps = r'''
$procs = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -ieq 'java.exe' -or $_.Name -ieq 'javaw.exe') -and
    $_.CommandLine -and (
        $_.CommandLine.ToLower().Contains('j:\mtg\xmage') -or
        $_.CommandLine.ToLower().Contains('xmagelauncher') -or
        $_.CommandLine.ToLower().Contains('mage.server.main') -or
        $_.CommandLine.ToLower().Contains('mage.client')
    )
}
foreach ($p in $procs) {
    Write-Output ("KILL PID=" + $p.ProcessId + " " + $p.Name)
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
'''
    return powershell(ps)

def write_rollback(path, previous, backup):
    text = f'''@echo off
setlocal
echo ================================================================
echo XMage Community Patch - ROLLBACK V4 UX FINAL R5
echo ================================================================
echo.
set "ACTIVE={ACTIVE_JAR}"
set "PREVIOUS={previous}"
set "BACKUP={backup}"
set /p CONFIRM=Restore previous client jar? [Y/N] 
if /I not "%CONFIRM%"=="Y" exit /b 1
if not exist "%PREVIOUS%" (
  echo ERROR: previous jar missing.
  echo Verified backup: %BACKUP%
  pause
  exit /b 1
)
if exist "%ACTIVE%" ren "%ACTIVE%" "mage-client-1.4.61.FAILED_V4_UX_R5.jar"
ren "%PREVIOUS%" "mage-client-1.4.61.jar"
echo.
echo Rollback completed.
pause
'''
    path.write_text(text.replace("\n", "\r\n"), encoding="utf-8")

def activate(candidate, candidate_sha):
    answer = input("\nActivate V4 UX FINAL R5 now? XMage will be closed if needed. [Y/N]: ").strip().lower()

    if answer not in ("y", "yes", "s", "si", "sí"):
        return {"activated": False, "previous": None, "backup": None, "rollback": None}

    if get_xmage_processes():
        print("[STEP] Closing XMage processes...")
        close_xmage()
    else:
        print("[OK] No XMage process detected.")

    time.sleep(3)
    need(not get_xmage_processes(), "Some XMage processes are still running")
    need(ACTIVE_JAR.is_file(), f"Active jar missing: {ACTIVE_JAR}")

    activation_dir = OUT / "activation-backups"
    activation_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    previous = ACTIVE_JAR.parent / f"mage-client-1.4.61.PRE_V4_UX_FINAL_R5_{stamp}.jar"
    backup = activation_dir / f"mage-client-1.4.61.pre-v4-ux-final-r5_{stamp}.jar"
    staged = ACTIVE_JAR.parent / f"mage-client-1.4.61.V4_UX_FINAL_R5_STAGE_{stamp}.jar"
    rollback = OUT / "ROLLBACK_XMAGE_V4_UX_FINAL_R5.cmd"

    before_sha = sha256_file(ACTIVE_JAR)

    print("[1/5] Verified backup...")
    shutil.copy2(ACTIVE_JAR, backup)
    need(sha256_file(backup) == before_sha, "Backup SHA mismatch")

    print("[2/5] Stage candidate...")
    shutil.copy2(candidate, staged)
    need(sha256_file(staged) == candidate_sha, "Staged SHA mismatch")

    print("[3/5] Prepare rollback...")
    write_rollback(rollback, previous, backup)

    print("[4/5] Atomic swap...")
    ACTIVE_JAR.rename(previous)
    try:
        staged.rename(ACTIVE_JAR)
    except Exception:
        if previous.is_file() and not ACTIVE_JAR.exists():
            previous.rename(ACTIVE_JAR)
        raise

    print("[5/5] Verify active...")
    need(sha256_file(ACTIVE_JAR) == candidate_sha, "Active SHA mismatch")

    return {
        "activated": True,
        "previous": str(previous),
        "backup": str(backup),
        "rollback": str(rollback),
    }

def main():
    print("================================================================")
    print("XMage Community Patch - V4 UX FINAL R5")
    print("================================================================")
    print()
    print("R5 fixes the R4 compile failure and keeps the same V4 UX goals.")
    print("Active XMage is untouched until the activation prompt.")
    print()

    OUT.mkdir(parents=True, exist_ok=True)
    source_backups = OUT / "source-backups"
    source_backups.mkdir(parents=True, exist_ok=True)

    base_checks = validate_expected_source()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    info_backup = source_backups / f"CardInfoPaneImpl.java.before-r5-import-fix_{stamp}.bak"
    shutil.copy2(CARD_INFO, info_backup)

    fixed_info, imports_changed = patch_imports(read(CARD_INFO))
    need("import java.awt.Dimension;" in fixed_info, "Dimension import still missing")
    need("import java.awt.Toolkit;" in fixed_info, "Toolkit import still missing")
    write(CARD_INFO, fixed_info)

    print("[OK] R5 import fix applied.")
    print("[STEP] Maven build...")

    cp = run_build()
    BUILD_LOG.write_text(cp.stdout, encoding="utf-8", errors="replace")
    need(cp.returncode == 0, f"Maven build failed. See: {BUILD_LOG}")

    built = SRC / "Mage.Client" / "target" / "mage-client-1.4.61.jar"
    need(built.is_file(), f"Built jar missing: {built}")

    candidate = OUT / "mage-client-1.4.61-XCP_V4_UX_FINAL_R5.jar"
    shutil.copy2(built, candidate)
    candidate_sha = sha256_file(candidate)

    print("[STEP] Static Smoke...")
    smoke = static_smoke(candidate)
    print("[OK] Static Smoke PASS.")

    activation = activate(candidate, candidate_sha)

    result = {
        "schema": 45,
        "phase": "XMAGE_V4_UX_FINAL_R5",
        "status": (
            "V4_UX_FINAL_R5_ACTIVATED_VISUAL_STABILITY_SMOKE_REQUIRED"
            if activation["activated"]
            else "V4_UX_FINAL_R5_BUILT_VERIFIED_NOT_ACTIVATED"
        ),
        "created_at": datetime.now().astimezone().isoformat(),
        "base_checks": base_checks,
        "imports_changed": imports_changed,
        "candidate_jar": str(candidate),
        "candidate_sha256": candidate_sha,
        "source_backup_card_info": str(info_backup),
        "build_log": str(BUILD_LOG),
        "static_smoke_log": str(SMOKE_LOG),
        "static_smoke": smoke,
        "activation": activation,
        "active_xmage_modified": activation["activated"],
        "v5_deferred": True,
        "next_gate": "V4_VISUAL_AND_STABILITY_SMOKE"
    }
    REPORT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    SUMMARY.write_text(
        "XMage Community Patch - V4 UX FINAL R5\n"
        "======================================\n\n"
        "RESULT: PASS\n"
        f"Status: {result['status']}\n"
        "R4 compile failure fixed: YES\n"
        "Missing CardInfoPaneImpl imports fixed: YES\n"
        "Bottom stack resize strip preserved: YES\n"
        "Context tooltip real-size measurement preserved: YES\n"
        "Popup on-screen reposition preserved: YES\n"
        "Set icon SMALL/LARGE fallback preserved: YES\n"
        "Stack order T-1 at top preserved: YES\n"
        "Hand/layout/phases Stable V4 preserved: YES\n"
        "Printing Selector V6 preserved: YES\n"
        "Static Smoke: PASS\n"
        "V5 fancy: DEFERRED\n"
        f"Candidate: {candidate}\n"
        f"Candidate SHA-256: {candidate_sha}\n"
        f"Activated: {activation['activated']}\n"
        f"Previous jar: {activation['previous']}\n"
        f"Verified backup: {activation['backup']}\n"
        f"Rollback: {activation['rollback']}\n"
        "Cleanup allowed: NO\n"
        "Next gate: V4_VISUAL_AND_STABILITY_SMOKE\n",
        encoding="utf-8"
    )

    print("\n=== V4 UX FINAL R5 COMPLETED ===")
    print(f"Summary: {SUMMARY}")
    if activation["activated"]:
        print("V4 UX FINAL R5 is ACTIVE. Open XMage normally and re-test.")
    else:
        print("Built and verified, but not activated.")
    print("Do NOT delete backups.")
    input("Press Enter to close...")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("V4 UX FINAL R5 FAILED.")
        print("Do NOT delete backups.")
        input("Press Enter to close...")
        raise SystemExit(1)
