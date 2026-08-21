@echo off
setlocal
set "SCRIPT=%~dp0PUBLICAR-FUENTE-EXACTA-v-1.2.12.ps1"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo ERROR: la fuente exacta no se publico. Codigo %RC%.
pause
exit /b %RC%

