@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - CONTROLLED ACTIVATION V2

echo ============================================================
echo XMage Community Patch - CONTROLLED ACTIVATION V2
echo ============================================================
echo.
echo V2 fixes the V1 false-positive process detector.
echo IMPORTANT: XMage client, server and launcher must be CLOSED.
echo Verified backups and rollback remain protected.
echo.
choice /C YN /N /M "Run CONTROLLED ACTIVATION V2 now? [Y/N] "
if errorlevel 2 exit /b 1
echo.
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0controlled_activation_v2.py"
) else (
    python "%~dp0controlled_activation_v2.py"
)
set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" (
 echo CONTROLLED ACTIVATION V2 DID NOT COMPLETE.
 echo Do not delete any backup folders.
) else (
 echo CONTROLLED ACTIVATION V2 COMPLETED.
 echo Do NOT delete backups. POST-ACTIVATION SMOKE TEST is still required.
)
echo.
pause
exit /b %RC%
