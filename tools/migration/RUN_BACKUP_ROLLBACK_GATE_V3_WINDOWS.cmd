@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - BACKUP + ROLLBACK GATE V3
echo ============================================================
echo XMage Community Patch - BACKUP + ROLLBACK GATE V3
echo ============================================================
echo SAFE MODE: candidate activation remains BLOCKED.
echo V3 uses process + filesystem discovery for the active XMage.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0backup_rollback_gate_v3.py"
) else (
  python "%~dp0backup_rollback_gate_v3.py"
)
set RC=%errorlevel%
echo.
if not "%RC%"=="0" (
  echo BACKUP + ROLLBACK GATE V3 FAILED OR STOPPED SAFELY.
  echo Nothing was activated.
) else (
  echo BACKUP + ROLLBACK GATE V3 COMPLETED SUCCESSFULLY.
  echo Candidate remains BLOCKED.
)
pause
exit /b %RC%
