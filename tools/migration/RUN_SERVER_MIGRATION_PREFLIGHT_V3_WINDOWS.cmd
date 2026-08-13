@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - SERVER MIGRATION PREFLIGHT V3

echo ================================================================
echo XMage Community Patch - SERVER MIGRATION PREFLIGHT V3
echo ================================================================
echo.
echo SAFE MODE: this does NOT replace the active server.
echo V3 avoids fragile PowerShell process inspection and uses DB lock probing.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0server_migration_preflight_v3.py"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python "%~dp0server_migration_preflight_v3.py"
    ) else (
        echo ERROR: Python 3 was not found in PATH.
        pause
        exit /b 1
    )
)

set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" (
    echo SERVER MIGRATION PREFLIGHT V3 FAILED OR STOPPED SAFELY.
    echo Active server was NOT replaced.
) else (
    echo SERVER MIGRATION PREFLIGHT V3 COMPLETED SUCCESSFULLY.
    echo Verified server rollback backup is ready. Activation has NOT happened yet.
)
echo.
pause
exit /b %RC%
