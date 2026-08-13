@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - SERVER POST ACTIVATION SMOKE V1

echo ================================================================
echo XMage Community Patch - SERVER POST ACTIVATION SMOKE V1
echo ================================================================
echo.
echo SAFE MODE: this does NOT delete backups and does NOT modify active files.
echo It launches the real XMage launcher so you can verify client+server together.
echo.
echo IMPORTANT: do NOT click Update in XMageLauncher.
echo Use only Launch Client and Server for this smoke test.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0server_post_activation_smoke_v1.py"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python "%~dp0server_post_activation_smoke_v1.py"
    ) else (
        echo ERROR: Python 3 was not found in PATH.
        pause
        exit /b 1
    )
)

set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" (
    echo SERVER POST ACTIVATION SMOKE V1 FAILED.
    echo Do NOT delete backups.
) else (
    echo SERVER POST ACTIVATION SMOKE V1 COMPLETED SUCCESSFULLY.
    echo Client and server are version-aligned.
)
echo.
pause
exit /b %RC%
