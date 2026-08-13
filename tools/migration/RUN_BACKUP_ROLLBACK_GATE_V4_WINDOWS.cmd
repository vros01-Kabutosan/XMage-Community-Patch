@echo off
setlocal
title XMage Community Patch - BACKUP + ROLLBACK GATE V4
cd /d "%~dp0"
echo ============================================================
echo XMage Community Patch - BACKUP + ROLLBACK GATE V4
echo ============================================================
echo SAFE MODE: candidate activation remains BLOCKED.
echo V4 filters backup, staging and release-candidate copies.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0backup_rollback_gate_v4.py"
) else (
  python "%~dp0backup_rollback_gate_v4.py"
)
set RC=%errorlevel%
echo.
if not "%RC%"=="0" echo Gate stopped safely with exit code %RC%.
pause
exit /b %RC%
