@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - CONTROLLED ACTIVATION PREFLIGHT V1

echo ============================================================
echo XMage Community Patch - CONTROLLED ACTIVATION PREFLIGHT V1
echo ============================================================
echo SAFE MODE: this step does NOT replace active XMage files.
echo It verifies candidate + backup and arms rollback for next gate.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0controlled_activation_preflight_v1.py"
) else (
    python "%~dp0controlled_activation_preflight_v1.py"
)

set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" (
    echo CONTROLLED ACTIVATION PREFLIGHT V1 FAILED SAFELY.
    echo Active XMage was NOT modified.
) else (
    echo CONTROLLED ACTIVATION PREFLIGHT V1 COMPLETED SUCCESSFULLY.
    echo Rollback is armed. Actual activation has NOT happened yet.
)
echo.
pause
exit /b %RC%
