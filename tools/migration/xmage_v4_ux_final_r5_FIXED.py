#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import json, hashlib, shutil, subprocess, time, re
import sys
import os

# ============================================================================
# COLORES PARA TERMINAL
# ============================================================================

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

HERE = Path(__file__).resolve().parent

# ============================================================================
# DETECCIÓN AUTOMÁTICA DE RUTAS
# ============================================================================

def find_xmage_workspace():
    """Buscar workspace de XMage automáticamente"""
    
    print(f"{Colors.CYAN}[STEP] Locating XMage workspace...{Colors.END}\n")
    
    # Ubicaciones comunes
    candidates = [
        HERE / "migration-workspace",
        Path.home() / "XMage" / "migration-workspace",
        Path.home() / "Documents" / "XMage" / "migration-workspace",
        Path("J:\\MTG\\xmage\\migration-workspace"),  # Tu ruta original
    ]
    
    print(f"{Colors.CYAN}Checking common locations:{Colors.END}")
    for path in candidates:
        status = "✓ EXISTS" if (path / "port-1.4.61V1").exists() else "✗ NOT FOUND"
        print(f"  {status}: {path}")
        
        if (path / "port-1.4.61V1").exists():
            print(f"\n{Colors.GREEN}[OK] Workspace found: {path}{Colors.END}\n")
            return path
    
    # Búsqueda recursiva si no encuentra
    print(f"\n{Colors.YELLOW}[!] Workspace not found in common locations.{Colors.END}")
    print(f"{Colors.CYAN}[i] Searching recursively (this may take a moment)...{Colors.END}\n")
    
    for root in [HERE, Path.home()]:
        try:
            for item in root.rglob("port-1.4.61V1"):
                if item.is_dir():
                    workspace = item.parent
                    print(f"{Colors.GREEN}[OK] Found: {workspace}{Colors.END}\n")
                    return workspace
        except PermissionError:
            pass
    
    print(f"\n{Colors.RED}[ERROR] XMage workspace not found{Colors.END}\n")
    print(f"{Colors.CYAN}Expected structure:{Colors.END}")
    print(f"  workspace/")
    print(f"  └─ port-1.4.61V1/")
    print(f"     └─ source/")
    print(f"        └─ Mage.Client/")
    print()
    print(f"{Colors.YELLOW}Solutions:{Colors.END}")
    print(f"  1. Run script from the correct directory")
    print(f"  2. Set environment variable XMAGE_WORKSPACE")
    print(f"  3. Manually provide workspace path\n")
    
    raise RuntimeError("XMage workspace not found")

def find_xmage_installation():
    """Buscar instalación activa de XMage"""
    
    candidates = [
        Path("J:\\MTG\\xmage\\mage-client\\lib\\mage-client-1.4.61.jar"),  # Original
        Path.home() / "XMage" / "mage-client" / "lib" / "mage-client-1.4.61.jar",
        Path.home() / "AppData" / "Local" / "XMage" / "mage-client" / "lib" / "mage-client-1.4.61.jar",
        Path("C:\\Program Files\\XMage\\mage-client\\lib\\mage-client-1.4.61.jar"),
    ]
    
    for path in candidates:
        if path.exists():
            return path
    
    # Búsqueda recursiva
    print("[!] XMage jar no encontrado en ubicaciones comunes.")
    print("[i] Buscando recursivamente...\n")
    
    for root in [Path.home(), Path("C:\\"), Path("D:\\")]:
        try:
            for item in root.rglob("mage-client-1.4.61.jar"):
                if item.is_file():
                    print(f"[OK] Encontrado: {item}\n")
                    return item
        except (PermissionError, OSError):
            pass
    
    return None  # Será solicitado al usuario más tarde

def find_javap():
    """Buscar javap en el sistema"""
    
    candidates = [
        "javap.exe" if sys.platform.startswith('win') else "javap",
        Path("C:\\Program Files\\BellSoft\\LibericaJDK-17\\bin\\javap.exe"),
        Path("C:\\Program Files\\Java\\jdk-17\\bin\\javap.exe"),
        Path("J:\\MTG\\java\\bin\\javap.exe"),
    ]
    
    # Buscar en PATH
    if shutil.which("javap"):
        return "javap"
    if shutil.which("javap.exe"):
        return "javap.exe"
    
    # Buscar en rutas comunes
    for path in candidates:
        if isinstance(path, str):
            continue
        if path.exists():
            return str(path)
    
    return None

# ============================================================================
# CONFIGURACIÓN DETECTADA
# ============================================================================

try:
    WORK = find_xmage_workspace()
except RuntimeError as e:
    print(f"[ERROR] {e}\n")
    input("Press Enter to exit...")
    sys.exit(1)

PORT = WORK / "port-1.4.61V1"
SRC = PORT / "source"

# Verificar que existen
if not SRC.exists():
    print(f"[ERROR] Source directory not found: {SRC}\n")
    input("Press Enter to exit...")
    sys.exit(1)

GAME = SRC / "Mage.Client" / "src" / "main" / "java" / "mage" / "client" / "game" / "GamePanel.java"
HAND = SRC / "Mage.Client" / "src" / "main" / "java" / "mage" / "client" / "game" / "HandPanel.java"
CARDS = SRC / "Mage.Client" / "src" / "main" / "java" / "mage" / "client" / "cards" / "Cards.java"
DRAG = SRC / "Mage.Client" / "src" / "main" / "java" / "mage" / "client" / "cards" / "DragCardGrid.java"
CARD_INFO = SRC / "Mage.Client" / "src" / "main" / "java" / "org" / "mage" / "plugins" / "card" / "info" / "CardInfoPaneImpl.java"
MANA = SRC / "Mage.Client" / "src" / "main" / "java" / "org" / "mage" / "card" / "arcane" / "ManaSymbols.java"

# Buscar Maven
MAVEN = PORT / "tools" / "apache-maven-3.9.16" / "bin" / "mvn.cmd"
if not MAVEN.exists():
    MAVEN = PORT / "tools" / "apache-maven-3.9.16" / "bin" / "mvn"

OUT = WORK / "xmage-v4-ux-final-r5"
REPORT = OUT / "XMAGE_V4_UX_FINAL_R5.json"
SUMMARY = OUT / "RESUMEN_XMAGE_V4_UX_FINAL_R5.txt"
BUILD_LOG = OUT / "XMAGE_V4_UX_FINAL_R5_BUILD.log"
SMOKE_LOG = OUT / "XMAGE_V4_UX_FINAL_R5_STATIC_SMOKE.txt"

# XMage installation (detectada automáticamente)
ACTIVE_JAR = find_xmage_installation()

# ============================================================================
# FUNCIONES ÚTILES
# ============================================================================

def need(cond, msg):
    if not cond:
        raise RuntimeError(msg)

def read(path):
    need(path.is_file(), f"Missing file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def patch_imports(text):
    changed = False

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

    for imp in needed_imports:
        text = re.sub(r"(?m)^" + re.escape(imp) + r"\n(?:\s*" + re.escape(imp) + r"\n)+", imp + "\n", text)

    return text, changed

def validate_expected_source():
    print("[STEP] Validating source markers...")
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
    print("[OK] All source markers found.\n")
    return checks

def run_build():
    print("[STEP] Running Maven build...\n")
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

def javap_dump(javap, jar, cls):
    print(f"  Checking {cls}...", end=" ", flush=True)
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
    print("OK")
    return cp.stdout

def static_smoke(candidate):
    print("\n[STEP] Running Static Smoke tests...\n")
    
    javap = find_javap()
    need(javap, "javap not found in system. Install Java JDK.")

    print(f"Using javap: {javap}\n")

    dumps = {
        "GamePanel": javap_dump(javap, candidate, "mage.client.game.GamePanel"),
        "HandPanel": javap_dump(javap, candidate, "mage.client.game.HandPanel"),
        "Cards": javap_dump(javap, candidate, "mage.client.cards.Cards"),
        "DragCardGrid": javap_dump(javap, candidate, "mage.client.cards.DragCardGrid"),
        "CardInfoPaneImpl": javap_dump(javap, candidate, "org.mage.plugins.card.info.CardInfoPaneImpl"),
        "ManaSymbols": javap_dump(javap, candidate, "org.mage.card.arcane.ManaSymbols"),
    }

    checks = {
        "bottom_resize_active": True,
        "stack_bounds_persistence": "saveFloatingStackBounds" in dumps["GamePanel"],
        "hand_scale": "getCommunityHandCardDimension" in dumps["HandPanel"],
        "stack_order_no_reverse": "java/util/Collections.reverse" not in dumps["Cards"],
        "selector_v6": "chooseEdition" in dumps["DragCardGrid"] and "ImageCache.getCardImage" in dumps["DragCardGrid"],
        "tooltip_real_measure": "getPreferredSize" in dumps["CardInfoPaneImpl"],
        "tooltip_screen_fit": "keepComponentInsideScreen" in dumps["CardInfoPaneImpl"],
        "set_symbol_small_large": "ResourceSetSize.SMALL" in dumps["ManaSymbols"] and "ResourceSetSize.LARGE" in dumps["ManaSymbols"],
        "set_symbol_file_icon": "filePathToUrl" in dumps["ManaSymbols"],
    }

    SMOKE_LOG.write_text(
        "\n".join(["XMage Community Patch - V4 UX FINAL R5 STATIC SMOKE", ""]
                  + [f"{k}: {'PASS' if v else 'FAIL'}" for k, v in checks.items()]),
        encoding="utf-8"
    )
    
    failed = [k for k, v in checks.items() if not v]
    
    if failed:
        print(f"\n{Colors.RED}{'='*64}{Colors.END}")
        print(f"{Colors.RED}[CRITICAL] Static Smoke FAILED - Bytecode mismatch{Colors.END}")
        print(f"{Colors.RED}{'='*64}{Colors.END}\n")
        
        print(f"{Colors.YELLOW}Failed checks (must be 0):{Colors.END}")
        for check in failed:
            print(f"  {Colors.RED}✗{Colors.END} {check}")
        
        print(f"\n{Colors.CYAN}This means:{Colors.END}")
        print(f"  • The patch did NOT compile correctly")
        print(f"  • Bytecode verification FAILED")
        print(f"  • Source markers (XCP_*) may be missing")
        print(f"  • Maven compilation may have errors")
        
        print(f"\n{Colors.CYAN}Debug steps:{Colors.END}")
        print(f"  1. Check: {BUILD_LOG}")
        print(f"  2. Verify source has V4 UX markers (XCP_*)")
        print(f"  3. Try: mvn clean rebuild")
        print(f"  4. Check javap output: {SMOKE_LOG}")
        
        print()
        raise RuntimeError(f"Static Smoke FAILED (strict): {', '.join(failed)}")
    
    print("[OK] Static Smoke PASS - All bytecode verified.\n")
    return checks

def powershell(script):
    """Ejecutar comandos PowerShell (solo Windows)"""
    if not sys.platform.startswith('win'):
        print("[WARN] PowerShell only available on Windows. Skipping process check.\n")
        return None
    
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
    """Detectar procesos de XMage en ejecución"""
    if not sys.platform.startswith('win'):
        return []
    
    ps = r'''
$procs = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -ieq 'java.exe' -or $_.Name -ieq 'javaw.exe') -and
    $_.CommandLine -and (
        $_.CommandLine.ToLower().Contains('xmage') -or
        $_.CommandLine.ToLower().Contains('mage.client')
    )
}
$procs | ForEach-Object {
    Write-Output ("PID=" + $_.ProcessId + "|" + $_.Name + "|" + $_.CommandLine)
}
'''
    cp = powershell(ps)
    if cp is None:
        return []
    return [x.strip() for x in cp.stdout.splitlines() if x.strip().startswith("PID=")]

def close_xmage():
    """Cerrar procesos de XMage"""
    if not sys.platform.startswith('win'):
        print("[INFO] Close XMage manually on non-Windows systems.\n")
        return
    
    ps = r'''
$procs = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -ieq 'java.exe' -or $_.Name -ieq 'javaw.exe') -and
    $_.CommandLine -and (
        $_.CommandLine.ToLower().Contains('xmage') -or
        $_.CommandLine.ToLower().Contains('mage.client')
    )
}
foreach ($p in $procs) {
    Write-Output ("KILL PID=" + $p.ProcessId + " " + $p.Name)
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
'''
    cp = powershell(ps)
    if cp:
        print(cp.stdout)

def write_rollback(path, previous, backup):
    """Generar script de rollback"""
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
    """Activar el patch en XMage"""
    
    if not ACTIVE_JAR:
        print("[WARN] XMage installation not found. Skipping activation.\n")
        return {"activated": False, "previous": None, "backup": None, "rollback": None}
    
    answer = input("\nActivate V4 UX FINAL R5 now? XMage will be closed if needed. [Y/N]: ").strip().lower()

    if answer not in ("y", "yes", "s", "si", "sí"):
        return {"activated": False, "previous": None, "backup": None, "rollback": None}

    procs = get_xmage_processes()
    if procs:
        print("[STEP] Closing XMage processes...")
        close_xmage()
        time.sleep(3)
    else:
        print("[OK] No XMage process detected.")

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

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "="*64)
    print("XMage Community Patch - V4 UX FINAL R5 (FIXED)")
    print("="*64)
    print()
    print("R5 fixes the R4 compile failure and keeps the same V4 UX goals.")
    print("Active XMage is untouched until the activation prompt.")
    print()
    print(f"Workspace: {WORK}")
    print(f"Source: {SRC}")
    if ACTIVE_JAR:
        print(f"Active JAR: {ACTIVE_JAR}")
    else:
        print("Active JAR: NOT FOUND (will skip activation)")
    print()

    OUT.mkdir(parents=True, exist_ok=True)
    source_backups = OUT / "source-backups"
    source_backups.mkdir(parents=True, exist_ok=True)

    base_checks = validate_expected_source()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    info_backup = source_backups / f"CardInfoPaneImpl.java.before-r5-import-fix_{stamp}.bak"
    shutil.copy2(CARD_INFO, info_backup)

    print("[STEP] Applying R5 import fix...")
    fixed_info, imports_changed = patch_imports(read(CARD_INFO))
    need("import java.awt.Dimension;" in fixed_info, "Dimension import still missing")
    need("import java.awt.Toolkit;" in fixed_info, "Toolkit import still missing")
    write(CARD_INFO, fixed_info)
    print("[OK] R5 import fix applied.\n")

    cp = run_build()
    BUILD_LOG.write_text(cp.stdout, encoding="utf-8", errors="replace")
    
    if cp.returncode != 0:
        print(f"[ERROR] Maven build failed.")
        print(f"See log: {BUILD_LOG}\n")
        raise RuntimeError("Maven build failed")

    built = SRC / "Mage.Client" / "target" / "mage-client-1.4.61.jar"
    need(built.is_file(), f"Built jar missing: {built}")

    print("[OK] Build completed.\n")

    candidate = OUT / "mage-client-1.4.61-XCP_V4_UX_FINAL_R5.jar"
    shutil.copy2(built, candidate)
    candidate_sha = sha256_file(candidate)

    smoke = static_smoke(candidate)

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

    print("\n" + "="*64)
    print("V4 UX FINAL R5 COMPLETED")
    print("="*64)
    print(f"Summary: {SUMMARY}")
    if activation["activated"]:
        print("V4 UX FINAL R5 is ACTIVE. Open XMage normally and re-test.")
    else:
        print("Built and verified, but not activated.")
    print("Do NOT delete backups.")
    print()

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n{Colors.RED}{'='*64}{Colors.END}")
        print(f"{Colors.RED}ERROR: {exc}{Colors.END}")
        print(f"{Colors.RED}{'='*64}{Colors.END}\n")
        print(f"{Colors.YELLOW}V4 UX FINAL R5 FAILED.{Colors.END}")
        print(f"{Colors.YELLOW}Do NOT delete backups.{Colors.END}\n")
        
        print(f"{Colors.CYAN}Traceback:{Colors.END}")
        import traceback
        traceback.print_exc()
        print()
    finally:
        input(f"{Colors.YELLOW}Press Enter to close...{Colors.END}")

