@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - V4 Deck Downloader Smoke Package

echo ================================================================
echo  XMage Community Patch - V1 DECK DOWNLOADER STATIC SMOKE/PACKAGE V4
echo ================================================================
echo.
echo SAFE MODE: this does NOT modify your active XMage installation.
echo It validates and packages ONLY the isolated 1.4.61V1 build.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0smoke_package_deck_downloader_v4.py"
) else (
    python "%~dp0smoke_package_deck_downloader_v4.py"
)

set RC=%errorlevel%
echo.
if %RC%==0 (
    echo STATIC SMOKE/PACKAGE GATE V4 PASSED.
    echo 1.4.61V1 is still BLOCKED pending isolated GUI smoke testing.
) else (
    echo STATIC SMOKE/PACKAGE GATE V4 FAILED SAFELY.
    echo Active XMage was NOT modified.
)
echo.
pause
exit /b %RC%
