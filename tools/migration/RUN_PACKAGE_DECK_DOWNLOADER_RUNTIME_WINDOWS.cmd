@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - Deck Downloader runtime capture

echo XMage Community Patch - DECK DOWNLOADER RUNTIME CAPTURE
echo =======================================================
echo SAFE MODE: reads the RC1 snapshot and creates one audit ZIP only.
echo Active XMage and 1.4.61V1 staging will NOT be modified.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 package_deck_downloader_runtime.py
) else (
  python package_deck_downloader_runtime.py
)
set ERR=%errorlevel%
echo.
if "%ERR%"=="0" (
  echo Capture completed successfully.
  echo Upload migration-workspace\reports\migration-analysis\deck-downloader-runtime\XMage_DECK_DOWNLOADER_RUNTIME_BUNDLE.zip
) else (
  echo FAILED with exit code %ERR%.
)
echo.
pause
exit /b %ERR%
