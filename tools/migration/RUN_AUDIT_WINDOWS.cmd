@echo off
setlocal
cd /d "%~dp0"
title XMage Community Patch - Protected Migration Audit

echo ============================================================
echo  XMage Community Patch - PROTECTED MIGRATION AUDIT
echo ============================================================
echo.
echo SAFE MODE: this does NOT modify your active XMage installation.
echo Network hardening: automatic retry + resume + SHA-256 verification.
echo It only downloads official/public packages into this tool folder,
echo compares RC1 with official 1.4.60V3 and prepares clean 1.4.61V1
echo in an isolated staging directory.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 audit_and_stage_robust.py
) else (
    where python >nul 2>nul
    if not %errorlevel%==0 (
        echo ERROR: Python 3 was not found.
        echo Install/use the Python 3 already used by the Community Patch tools.
        pause
        exit /b 1
    )
    python audit_and_stage_robust.py
)

if not %errorlevel%==0 (
    echo.
    echo Audit stopped safely. Active XMage was NOT modified.
    pause
    exit /b 1
)

echo.
echo Audit finished. Send RESUMEN_AUDITORIA.txt to the project maintainer.
pause
