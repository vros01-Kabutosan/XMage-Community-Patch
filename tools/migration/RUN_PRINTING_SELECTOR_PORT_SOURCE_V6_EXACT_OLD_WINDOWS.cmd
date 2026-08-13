@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - PRINTING SELECTOR PORT SOURCE V6 EXACT OLD

echo ================================================================
echo XMage Community Patch - PRINTING SELECTOR PORT SOURCE V6 EXACT OLD
echo ================================================================
echo.
echo SAFE MODE: patches only isolated 1.4.61V1 workspace source.
echo Active XMage is NOT modified.
echo.
echo V6 restores the exact old working selector behavior:
echo - ImageCache preview
echo - JLabel + ImageIcon miniature
echo - allCards same-name replacement
echo - all matching copies change automatically
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0printing_selector_port_source_v6_exact_old.py"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python "%~dp0printing_selector_port_source_v6_exact_old.py"
    ) else (
        echo ERROR: Python 3 was not found in PATH.
        pause
        exit /b 1
    )
)

set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" (
    echo PRINTING SELECTOR V6 EXACT OLD FAILED.
    echo Active XMage was NOT modified.
) else (
    echo PRINTING SELECTOR V6 EXACT OLD PASSED.
    echo Candidate jar was built but NOT activated.
)
echo.
pause
exit /b %RC%
