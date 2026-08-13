@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - BACKUP + ROLLBACK GATE V1

echo ============================================================
echo XMage Community Patch - BACKUP + ROLLBACK GATE V1
echo ============================================================
echo SAFE MODE: candidate activation remains BLOCKED.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0backup_rollback_gate_v1.py"
) else (
  python "%~dp0backup_rollback_gate_v1.py"
)
set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" (
  echo BACKUP + ROLLBACK GATE V1 STOPPED SAFELY.
  echo Candidate was NOT activated.
) else (
  echo BACKUP + ROLLBACK GATE V1 COMPLETED SUCCESSFULLY.
  echo Candidate activation remains BLOCKED.
)
echo.
pause
exit /b %RC%
