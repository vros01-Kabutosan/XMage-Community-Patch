@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - Three-Way Source Compare

echo XMage Community Patch - THREE-WAY RECONSTRUCTED SOURCE COMPARE
echo =============================================================
echo.
echo SAFE MODE: this only writes reports inside migration-workspace.
echo It does NOT modify active XMage or activate/modify 1.4.61V1 staging.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 compare_reconstructed_sources_threeway.py
) else (
    python compare_reconstructed_sources_threeway.py
)

set RC=%errorlevel%
echo.
if not "%RC%"=="0" (
    echo SOURCE THREE-WAY comparison FAILED. 1.4.61V1 remains BLOCKED.
) else (
    echo Source comparison completed successfully.
    echo Send migration-workspace\reports\migration-analysis\source-threeway\RESUMEN_SOURCE_THREEWAY.txt
    echo to the project maintainer.
)
echo.
pause
exit /b %RC%
