@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - Non-card three-way classifier

echo XMage Community Patch - NON-CARD THREE-WAY CLASSIFIER
echo ====================================================
echo SAFE MODE: this only writes reports inside migration-workspace.
echo It does NOT modify your active XMage installation.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 classify_noncard_hash_topology.py
) else (
  python classify_noncard_hash_topology.py
)

set ERR=%errorlevel%
echo.
if not "%ERR%"=="0" (
  echo ERROR: classifier exited with code %ERR%.
  echo Active XMage was NOT modified. 1.4.61V1 remains BLOCKED.
) else (
  echo Classification finished successfully.
  echo Send migration-workspace\reports\migration-analysis\bytecode-analysis\noncard-classification\RESUMEN_NONCARD_CLASIFICACION.txt
  echo to the project maintainer.
)
echo.
pause
exit /b %ERR%
