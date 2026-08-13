@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - CONTROLLED INSTALL PREP V1

echo ============================================================
echo XMage Community Patch - CONTROLLED INSTALL PREP V1
echo ============================================================
echo SAFE MODE: active XMage will NOT be modified.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0prepare_controlled_install_v1.py"
) else (
    python "%~dp0prepare_controlled_install_v1.py"
)

set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" (
    echo CONTROLLED INSTALL PREP V1 FAILED SAFELY.
    echo Active XMage was NOT modified.
) else (
    echo CONTROLLED INSTALL PREP V1 COMPLETED SUCCESSFULLY.
    echo Active XMage was NOT modified. Activation remains BLOCKED.
)
echo.
pause
exit /b %RC%
