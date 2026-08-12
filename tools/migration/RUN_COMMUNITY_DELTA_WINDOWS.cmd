@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - COMMUNITY DELTA

echo XMage Community Patch - COMMUNITY_DELTA
echo =======================================
echo.
echo SAFE MODE: this does NOT modify your active XMage installation.
echo It identifies which RC1 changes actually need to survive on 1.4.61V1.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 community_delta.py
) else (
    python community_delta.py
)

set EXITCODE=%errorlevel%
echo.
if not "%EXITCODE%"=="0" (
    echo COMMUNITY_DELTA finished with ERROR %EXITCODE%.
) else (
    echo COMMUNITY_DELTA finished successfully.
    echo Send migration-workspace\reports\migration-analysis\community-delta\COMMUNITY_DELTA_SUMMARY.txt
    echo to the project maintainer.
)
echo.
pause
exit /b %EXITCODE%
