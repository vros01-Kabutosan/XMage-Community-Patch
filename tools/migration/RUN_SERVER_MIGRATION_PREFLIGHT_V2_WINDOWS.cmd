@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - SERVER MIGRATION PREFLIGHT V2

echo ================================================================
echo XMage Community Patch - SERVER MIGRATION PREFLIGHT V2
echo ================================================================
echo.
echo SAFE MODE: active server will NOT be replaced.
echo V2 checks running server processes and H2 DB locks before backup.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0server_migration_preflight_v2.py"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    python "%~dp0server_migration_preflight_v2.py"
  ) else (
    echo ERROR: Python 3 was not found in PATH.
    pause
    exit /b 1
  )
)

set RC=%errorlevel%
echo.
if "%RC%"=="0" (
  echo SERVER MIGRATION PREFLIGHT V2 COMPLETED SUCCESSFULLY.
) else (
  echo SERVER MIGRATION PREFLIGHT V2 FAILED OR STOPPED SAFELY.
  echo Active server was NOT intentionally modified.
)
echo.
pause
exit /b %RC%
