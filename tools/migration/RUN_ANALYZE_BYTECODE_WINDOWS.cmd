@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - Semantic Bytecode Analyzer

echo XMage Community Patch - SEMANTIC BYTECODE ANALYZER
echo ==================================================
echo.
echo SAFE MODE: this does NOT modify your active XMage installation.
echo It filters false-positive JAR differences before source migration.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 analyze_bytecode.py
) else (
    python analyze_bytecode.py
)

set EXITCODE=%errorlevel%
echo.
if not "%EXITCODE%"=="0" (
    echo Analyzer finished with ERROR %EXITCODE%.
) else (
    echo Analyzer finished successfully.
    echo Send migration-workspace\reports\migration-analysis\bytecode-analysis\RESUMEN_BYTECODE_SEMANTICO.txt
    echo and semantic-bytecode-analysis.json to the project maintainer.
)
echo.
pause
exit /b %EXITCODE%
