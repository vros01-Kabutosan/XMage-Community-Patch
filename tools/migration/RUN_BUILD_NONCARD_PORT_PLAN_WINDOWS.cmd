@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - Non-card surgical port plan

echo XMage Community Patch - NON-CARD SURGICAL PORT PLAN
echo ==================================================
echo.
echo SAFE MODE: this creates reports and candidate patches only.
echo It does NOT modify active XMage or 1.4.61V1 staging.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 build_noncard_port_plan.py
) else (
  python build_noncard_port_plan.py
)
set ERR=%errorlevel%
echo.
if not "%ERR%"=="0" echo FAILED with exit code %ERR%.
pause
exit /b %ERR%
