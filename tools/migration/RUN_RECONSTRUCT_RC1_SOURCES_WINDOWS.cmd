@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - RC1 Source Reconstruction

echo XMage Community Patch - RC1 SOURCE RECONSTRUCTION
echo =================================================
echo.
echo SAFE MODE: this reconstructs Java source evidence from RC1 binaries.
echo It DOES NOT modify your active XMage or activate 1.4.61V1.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 reconstruct_rc1_noncard_sources.py
) else (
  python reconstruct_rc1_noncard_sources.py
)

if errorlevel 1 (
  echo.
  echo Reconstruction FAILED. Active XMage was not modified.
  pause
  exit /b 1
)

echo.
echo Reconstruction completed successfully.
echo Send migration-workspace\reports\migration-analysis\source-reconstruction\RESUMEN_RECONSTRUCCION_RC1.txt to the project maintainer.
pause
