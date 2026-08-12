@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - Three-Way Migration Analyzer

echo XMage Community Patch - THREE-WAY MIGRATION ANALYZER
echo =====================================================
echo.
echo SAFE MODE: this does NOT modify your active XMage installation.
echo It analyzes official 1.4.60V3 vs Community RC1 vs official 1.4.61V1.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 analyze_migration.py
) else (
    python analyze_migration.py
)

set EXITCODE=%errorlevel%
echo.
if not "%EXITCODE%"=="0" (
    echo Analyzer ended with error code %EXITCODE%.
) else (
    echo Analyzer finished successfully.
    echo Send migration-workspace\reports\migration-analysis\RESUMEN_MIGRACION_3VIAS.txt
    echo to the project maintainer before activating 1.4.61V1.
)
echo.
pause
exit /b %EXITCODE%
