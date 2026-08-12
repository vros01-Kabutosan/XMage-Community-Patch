@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - Package non-card review bundle

echo XMage Community Patch - PACKAGE NON-CARD REVIEW BUNDLE
echo ======================================================
echo.
echo SAFE MODE: packages migration evidence only.
echo It does NOT modify active XMage, V1 staging, or apply patches.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 package_noncard_review_bundle.py
) else (
  python package_noncard_review_bundle.py
)
set ERR=%errorlevel%
echo.
if not "%ERR%"=="0" echo FAILED with exit code %ERR%.
pause
exit /b %ERR%
