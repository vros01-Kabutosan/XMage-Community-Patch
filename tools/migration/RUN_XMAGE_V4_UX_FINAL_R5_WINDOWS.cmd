@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - V4 UX FINAL R5

echo ================================================================
echo XMage Community Patch - V4 UX FINAL R5
echo ================================================================
echo.
echo R5 fixes the R4 build failure and preserves all V4 UX fixes:
echo - bottom stack resize strip
echo - tooltip sized to real HTML content
echo - popup kept inside screen
echo - set icon SMALL/LARGE fallback
echo - stack T-1 at top
echo.
echo V5 fancy is still DEFERRED.
echo Active XMage is untouched until the activation prompt.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0xmage_v4_ux_final_r5.py"
) else (
    python "%~dp0xmage_v4_ux_final_r5.py"
)

set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" (
    echo V4 UX FINAL R5 FAILED.
    echo Do NOT delete backups.
) else (
    echo V4 UX FINAL R5 FINISHED.
)
echo.
pause
exit /b %RC%
