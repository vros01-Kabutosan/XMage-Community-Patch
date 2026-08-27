@echo off
setlocal EnableExtensions EnableDelayedExpansion
title XMage RC1.3 - Arranque cliente T - v-1.0.1

set "ACTIVE_ROOT=J:\mtg\xmage"
set "CLIENT_ROOT=%ACTIVE_ROOT%\client"
set "CLIENT_LIB=%CLIENT_ROOT%\lib"
set "LOG_ROOT=J:\mtg\_LOGS"
set "STAMP="
for /f "delims=" %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%T"
if not defined STAMP set "STAMP=manual"
set "LOG_DIR=%LOG_ROOT%\launch_T_RC1.3-v-1.0.1_%STAMP%"
set "TRANSCRIPT=%LOG_DIR%\launch_transcript.log"
if not exist "%LOG_DIR%\." mkdir "%LOG_DIR%"

call :LOG "START arranque directo del cliente XMage RC1.3 con indicador T"
call :LOG "Instalacion=%ACTIVE_ROOT%"
if not exist "%CLIENT_ROOT%\." goto FAIL_CLIENT_ROOT
if not exist "%CLIENT_LIB%\mage-client-1.4.61.jar" goto FAIL_CLIENT_JAR
if not exist "%CLIENT_LIB%\mage-common-1.4.61.jar" goto FAIL_COMMON_JAR

set "JAVA_CMD="
if exist "%TEMP%\xmage-tools\jdk17\." for /r "%TEMP%\xmage-tools\jdk17" %%P in (java.exe) do if not defined JAVA_CMD set "JAVA_CMD=%%P"
if not exist "%JAVA_CMD%" set "JAVA_CMD=C:\Program Files\BellSoft\LibericaJDK-17\bin\java.exe"
if not exist "%JAVA_CMD%" set "JAVA_CMD="
if not exist "%JAVA_CMD%" for /f "delims=" %%P in ('where java.exe 2^>nul') do if not defined JAVA_CMD set "JAVA_CMD=%%P"
if not defined JAVA_CMD goto FAIL_JAVA

call :LOG "Java seleccionado=%JAVA_CMD%"
"%JAVA_CMD%" -version > "%LOG_DIR%\java_version.log" 2>&1
findstr /c:"17." "%LOG_DIR%\java_version.log" >nul
if errorlevel 1 goto FAIL_JAVA

call :LOG "Cliente y dependencias presentes."
call :LOG "Iniciando mage.client.MageFrame con classpath completo."
pushd "%CLIENT_ROOT%"
"%JAVA_CMD%" -Xms512m -Xmx4g -Dfile.encoding=UTF-8 -Dsun.java2d.uiScale=1.5 -cp "%CLIENT_LIB%\*" mage.client.MageFrame > "%LOG_DIR%\client_stdout.log" 2> "%LOG_DIR%\client_stderr.log"
set "CLIENT_RC=!ERRORLEVEL!"
popd
call :LOG "Proceso cliente finalizado con codigo=%CLIENT_RC%"
if not "%CLIENT_RC%"=="0" goto FAIL_CLIENT_START
echo.
echo CLIENTE CERRADO SIN ERROR. LOG: %LOG_DIR%
pause
exit /b 0

:FAIL_CLIENT_ROOT
call :FAIL "No existe la carpeta client de la instalacion."
exit /b 1
:FAIL_CLIENT_JAR
call :FAIL "No existe mage-client-1.4.61.jar en client\lib."
exit /b 1
:FAIL_COMMON_JAR
call :FAIL "No existe mage-common-1.4.61.jar en client\lib."
exit /b 1
:FAIL_JAVA
call :FAIL "No se encontro un Java 17 valido."
exit /b 1
:FAIL_CLIENT_START
call :FAIL "El cliente no pudo iniciar. Revisar client_stderr.log y client_stdout.log."
exit /b 1

:FAIL
call :LOG "FAIL: %~1"
echo.
echo ARRANQUE FALLIDO: %~1
echo LOG: %LOG_DIR%
echo.
pause
exit /b 1

:LOG
>>"%TRANSCRIPT%" echo [%DATE% %TIME%] %~1
echo %~1
exit /b 0
