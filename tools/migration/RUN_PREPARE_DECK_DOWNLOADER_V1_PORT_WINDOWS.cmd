@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - Build Deck Downloader port on 1.4.61V1

echo XMage Community Patch - ISOLATED 1.4.61V1 PORT BUILD
echo =====================================================
echo.
echo This clones official 1.4.61V1 into migration-workspace,
echo applies the Deck Downloader port there and compiles it.
echo.
echo SAFE MODE: active XMage and clean V1 staging are NOT modified.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 prepare_deck_downloader_v1_port.py
) else (
  python prepare_deck_downloader_v1_port.py
)
set ERR=%errorlevel%
echo.
if "%ERR%"=="0" (
  echo BUILD COMPLETED SUCCESSFULLY.
  echo Send migration-workspace\port-1.4.61V1\reports\RESUMEN_PORT_BUILD.txt
) else (
  echo BUILD FAILED OR WAS BLOCKED. Exit code %ERR%.
  echo Nothing was installed into active XMage.
  echo Check migration-workspace\port-1.4.61V1\reports\maven-build.log if present.
)
echo.
pause
exit /b %ERR%
