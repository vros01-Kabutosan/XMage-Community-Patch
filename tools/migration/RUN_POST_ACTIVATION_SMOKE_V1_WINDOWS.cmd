@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - POST ACTIVATION SMOKE V1

echo ================================================================
echo XMage Community Patch - POST ACTIVATION SMOKE V1
echo ================================================================
echo.
echo This validates the newly activated 1.4.61V1 installation.
echo It DOES NOT delete backups.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0post_activation_smoke_v1.py"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python "%~dp0post_activation_smoke_v1.py"
    ) else (
        echo ERROR: Python 3 was not found in PATH.
        echo Install/use the same Python environment used by the previous migration gates.
        pause
        exit /b 1
    )
)

set RC=%errorlevel%
echo.
if not "%RC%"=="0" (
    echo POST ACTIVATION SMOKE V1 FAILED OR WAS CANCELLED.
    echo DO NOT DELETE ANY BACKUPS.
) else (
    echo POST ACTIVATION SMOKE V1 COMPLETED SUCCESSFULLY.
    echo DO NOT DELETE BACKUPS YET. FINALIZE V1 is still required.
)
echo.
pause
exit /b %RC%
