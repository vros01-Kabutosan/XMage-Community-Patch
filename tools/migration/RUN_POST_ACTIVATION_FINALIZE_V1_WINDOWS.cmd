@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - POST ACTIVATION FINALIZE V1

echo ================================================================
echo XMage Community Patch - POST ACTIVATION FINALIZE V1
echo ================================================================
echo.
echo Final migration bookkeeping and integrity gate.
echo NO backups, images, decks or rollback data will be deleted.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0post_activation_finalize_v1.py"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    python "%~dp0post_activation_finalize_v1.py"
  ) else (
    echo ERROR: Python 3 was not found in PATH.
    pause
    exit /b 1
  )
)

set RC=%errorlevel%
echo.
if "%RC%"=="0" (
  echo POST ACTIVATION FINALIZE V1 COMPLETED SUCCESSFULLY.
  echo Migration 1.4.61V1 is formally finalized.
) else (
  echo POST ACTIVATION FINALIZE V1 FAILED.
  echo Keep all backups and rollback data.
)
echo.
pause
exit /b %RC%
