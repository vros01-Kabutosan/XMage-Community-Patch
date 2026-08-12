@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - Deck Downloader Source Audit

echo XMage Community Patch - DECK DOWNLOADER SOURCE AUDIT
echo =====================================================
echo.
echo SAFE MODE: active XMage and 1.4.61V1 staging will NOT be modified.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 extract_deckdownloader_sources.py
) else (
  python extract_deckdownloader_sources.py
)

set RC=%errorlevel%
echo.
if not "%RC%"=="0" echo Audit failed with exit code %RC%.
if "%RC%"=="0" echo Audit finished successfully.
echo.
pause
exit /b %RC%
