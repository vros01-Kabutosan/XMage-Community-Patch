@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - Conflict Triage

echo XMage Community Patch - CONFLICT TRIAGE
echo ========================================
echo.
echo SAFE MODE: this does NOT modify your active XMage installation.
echo It converts semantic conflicts into a deduplicated source-file worklist.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 triage_conflicts.py
) else (
    python triage_conflicts.py
)

set EXITCODE=%errorlevel%
echo.
if not "%EXITCODE%"=="0" (
    echo Conflict triage finished with ERROR %EXITCODE%.
) else (
    echo Conflict triage finished successfully.
    echo Send migration-workspace\reports\migration-analysis\bytecode-analysis\conflict-triage\RESUMEN_CONFLICTOS.txt
    echo to the project maintainer.
)
echo.
pause
exit /b %EXITCODE%
