@echo off
setlocal
title XMage Community Patch - BACKUP + ROLLBACK GATE V2
cd /d "%~dp0"
echo ============================================================
echo XMage Community Patch - BACKUP + ROLLBACK GATE V2
echo ============================================================
echo SAFE MODE: candidate activation remains BLOCKED.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 backup_rollback_gate_v1.py
) else (
  python backup_rollback_gate_v1.py
)
set RC=%errorlevel%
echo.
if not "%RC%"=="0" echo Gate stopped safely with error code %RC%.
pause
exit /b %RC%
