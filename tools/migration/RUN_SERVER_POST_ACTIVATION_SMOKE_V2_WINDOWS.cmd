@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - SERVER POST ACTIVATION SMOKE V2

echo ================================================================
echo XMage Community Patch - SERVER POST ACTIVATION SMOKE V2
echo ================================================================
echo.
echo SAFE MODE: this does NOT delete backups and does NOT modify active files.
echo V2 accepts client/server build timestamp drift if both are 1.4.61.
echo.
echo IMPORTANT: do NOT click Update in XMageLauncher.
echo Use only Launch Client and Server for this smoke test.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0server_post_activation_smoke_v2.py"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python "%~dp0server_post_activation_smoke_v2.py"
    ) else (
        echo ERROR: Python 3 was not found in PATH.
        pause
        exit /b 1
    )
)

set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" (
    echo SERVER POST ACTIVATION SMOKE V2 FAILED.
    echo Do NOT delete backups.
) else (
    echo SERVER POST ACTIVATION SMOKE V2 COMPLETED SUCCESSFULLY.
    echo Client and server are version-aligned at 1.4.61.
)
echo.
pause
exit /b %RC%
