@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - CONTROLLED SERVER ACTIVATION V1

echo ================================================================
echo XMage Community Patch - CONTROLLED SERVER ACTIVATION V1
echo ================================================================
echo.
echo WARNING: this gate CAN replace the active local mage-server.
echo It does NOT touch mage-client, images, decks, launcher or installed.properties.
echo Rollback and verified backup are preserved.
echo.
echo IMPORTANT: close XMage Client, Server and Launcher before continuing.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0controlled_server_activation_v1.py"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python "%~dp0controlled_server_activation_v1.py"
    ) else (
        echo ERROR: Python 3 was not found in PATH.
        pause
        exit /b 1
    )
)

set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" (
    echo CONTROLLED SERVER ACTIVATION V1 FAILED OR STOPPED SAFELY.
    echo Keep all backups and rollback data.
) else (
    echo CONTROLLED SERVER ACTIVATION V1 COMPLETED SUCCESSFULLY.
    echo Server post-activation smoke test is still required.
)
echo.
pause
exit /b %RC%
