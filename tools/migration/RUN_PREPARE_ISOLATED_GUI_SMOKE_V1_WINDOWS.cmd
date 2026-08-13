@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - Isolated GUI Smoke Prep V1

echo ================================================================
echo  XMage Community Patch - ISOLATED GUI SMOKE PREPARATION V1
echo ================================================================
echo.
echo SAFE MODE: active XMage will NOT be modified.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
 py -3 "%~dp0prepare_isolated_gui_smoke_v1.py"
) else (
 python "%~dp0prepare_isolated_gui_smoke_v1.py"
)
set RC=%errorlevel%
echo.
if %RC%==0 (
 echo ISOLATED GUI SMOKE PREPARATION V1 PASSED.
 echo Send the final screen before launching anything else.
) else (
 echo PREPARATION FAILED SAFELY. Active XMage was NOT modified.
)
echo.
pause
exit /b %RC%
