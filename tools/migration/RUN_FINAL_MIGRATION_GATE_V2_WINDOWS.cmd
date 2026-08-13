@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - FINAL MIGRATION GATE V2

echo ============================================================
echo XMage Community Patch - FINAL MIGRATION GATE V2
echo ============================================================
echo SAFE MODE: active XMage will NOT be modified.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0final_migration_gate_v2.py"
) else (
    python "%~dp0final_migration_gate_v2.py"
)

set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" (
    echo FINAL MIGRATION GATE V2 FAILED SAFELY.
    echo Active XMage was NOT modified.
) else (
    echo FINAL MIGRATION GATE V2 COMPLETED SUCCESSFULLY.
    echo Active XMage was NOT modified.
)
echo.
pause
exit /b %RC%
