@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - CONTROLLED ACTIVATION V1

echo ============================================================
echo XMage Community Patch - CONTROLLED ACTIVATION V1
echo ============================================================
echo.
echo IMPORTANT: CLOSE XMage client, server and launcher before continuing.
echo This is the first gate allowed to replace the active XMage client.
echo Verified backups and rollback will be preserved.
echo.
choice /C YN /N /M "Run CONTROLLED ACTIVATION V1 now? [Y/N] "
if errorlevel 2 exit /b 1
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0controlled_activation_v1.py"
) else (
    python "%~dp0controlled_activation_v1.py"
)

set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" (
    echo CONTROLLED ACTIVATION V1 DID NOT COMPLETE.
    echo Read the message above. Do not delete any backup folders.
) else (
    echo CONTROLLED ACTIVATION V1 COMPLETED.
    echo Do NOT delete backups. POST-ACTIVATION SMOKE TEST is still required.
)
echo.
pause
exit /b %RC%
