@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - SERVER MIGRATION PREFLIGHT V1
py -3 server_migration_preflight_v1.py
if errorlevel 1 (
  echo.
  echo SERVER MIGRATION PREFLIGHT V1 FAILED OR STOPPED SAFELY.
  pause
  exit /b 1
)
echo.
echo SERVER MIGRATION PREFLIGHT V1 COMPLETED SUCCESSFULLY.
pause
