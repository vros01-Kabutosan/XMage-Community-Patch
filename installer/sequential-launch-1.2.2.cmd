@echo off
setlocal EnableExtensions EnableDelayedExpansion

title XMage Community Patch RC1 1.4.61 - Sequential Launcher 1.2.2

rem ================================================================
rem XMage Community Patch RC1 1.4.61
rem Sequential launcher 1.2.2
rem
rem This file only verifies the prepared installation and launches
rem the official launcher. It does not rebuild, relink, or rewrite
rem installed.properties, mage-client, mage-server, or any config.
rem ================================================================

set "SCRIPT_VERSION=1.2.2"
set "SCRIPT_DIR=%~dp0"
set "ROOT=%SCRIPT_DIR%"
set "EXPECTED_ROOT=J:\xmage repositorio\XMage-Community-Patch-hardening-update-architecture\tools\migration\XMage-Community-Patch-RC1-1.4.61-Official-Clone-v-1.2-CORE\XMage-Community-Patch-RC1-1.4.61-Official-Clone-v-1.2"

rem If the file is launched from another folder, use the exact prepared
rem installation path supplied for this checkpoint when it exists.
if not exist "%ROOT%java\jre1.8.0_201\bin\java.exe" if exist "%EXPECTED_ROOT%\java\jre1.8.0_201\bin\java.exe" set "ROOT=%EXPECTED_ROOT%\"

set "JAVA=%ROOT%java\jre1.8.0_201\bin\java.exe"
set "LAUNCHER=%ROOT%XMageLauncher-0.3.8.jar"
set "INSTALLED_PROPERTIES=%ROOT%installed.properties"
set "CLIENT_LINK=%ROOT%xmage\mage-client"
set "SERVER_LINK=%ROOT%xmage\mage-server"
set "LOG_DIR=%ROOT%logs"

if not exist "%JAVA%" goto ROOT_ERROR
if not exist "%LAUNCHER%" goto ROOT_ERROR
if not exist "%INSTALLED_PROPERTIES%" goto ROOT_ERROR
if not exist "%CLIENT_LINK%" goto ROOT_ERROR
if not exist "%SERVER_LINK%" goto ROOT_ERROR

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
if not exist "%LOG_DIR%" goto ROOT_ERROR

set "STAMP="
for /f "delims=" %%I in ('powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "Get-Date -Format yyyyMMdd-HHmmss-fff" 2^>nul') do if not defined STAMP set "STAMP=%%I"
if not defined STAMP set "STAMP=%RANDOM%-%RANDOM%"

set "SEQUENTIAL_LOG=%LOG_DIR%\sequential-launch-%STAMP%.log"
set "LAUNCHER_LIVE_LOG=%LOG_DIR%\launcher-live-%STAMP%.log"
set "LAUNCHER_LIVE_ERRORS_LOG=%LOG_DIR%\launcher-live-errors-%STAMP%.log"
set "LAUNCHER_CONTROL_LOG=%LOG_DIR%\launcher-control-%STAMP%.log"
set "LAUNCHER_CONTROL_ERRORS_LOG=%LOG_DIR%\launcher-control-errors-%STAMP%.log"
set "PID_FILE=%TEMP%\xmage-launcher-%STAMP%.pid"

>"%SEQUENTIAL_LOG%" echo [!DATE! !TIME!] XMage sequential launcher !SCRIPT_VERSION! started.
>"%LAUNCHER_CONTROL_LOG%" echo [!DATE! !TIME!] Launcher control log created.
>"%LAUNCHER_CONTROL_ERRORS_LOG%" echo [!DATE! !TIME!] Launcher control error log created.

call :log "[XMAGE] Script iniciado correctamente."
call :log "[XMAGE] Version del script: !SCRIPT_VERSION!"
call :log "[XMAGE] Log: !SEQUENTIAL_LOG!"
call :log "[XMAGE] UI blindada: -Dsun.java2d.uiScale=1.5"
call :control "Prepared root: !ROOT!"
call :control "Java: !JAVA!"
call :control "Launcher: !LAUNCHER!"
call :control "Separate live stdout: !LAUNCHER_LIVE_LOG!"
call :control "Separate live stderr: !LAUNCHER_LIVE_ERRORS_LOG!"

rem ================================================================
rem 1/4 - Verify the exact Java runtime without changing anything.
rem ================================================================
set "JAVA_VERSION_FILE=%TEMP%\xmage-java-version-%STAMP%.tmp"
"%JAVA%" -version >"%JAVA_VERSION_FILE%" 2>&1
findstr /c:"1.8.0_201" "%JAVA_VERSION_FILE%" >nul 2>&1
if errorlevel 1 (
    call :log "ERROR: No se ha verificado Java 8u201 en la ruta preparada."
    call :control_error "Java version verification failed."
    if exist "%JAVA_VERSION_FILE%" del /q "%JAVA_VERSION_FILE%" >nul 2>&1
    goto FAIL
)
if exist "%JAVA_VERSION_FILE%" del /q "%JAVA_VERSION_FILE%" >nul 2>&1
call :log "[1/4] Java 8u201 detectado."

rem ================================================================
rem 2/4 - Verify the already prepared server port.
rem ================================================================
call :log "[2/4] Comprobando el puerto 17171..."
call :port_open
if not errorlevel 1 (
    call :log "[XMAGE] El servidor ya esta escuchando. Se reutiliza."
    call :control "Server port 17171 already listening; reuse requested."
) else (
    call :log "[XMAGE] El servidor aun no responde; se esperara sin modificarlo."
    call :control "Server port 17171 not ready; active polling started."
)

rem ================================================================
rem 3/4 - Active polling. No server process is started or modified.
rem ================================================================
call :log "[3/4] Esperando a que el servidor abra 17171..."
set "SERVER_READY="
for /l %%N in (1,1,30) do (
    call :port_open
    if not errorlevel 1 (
        set "SERVER_READY=1"
        goto SERVER_READY
    )
    timeout /t 1 /nobreak >nul 2>&1
)

:SERVER_READY
if not defined SERVER_READY (
    call :log "ERROR: El servidor no llego a estar disponible en 127.0.0.1:17171."
    call :control_error "Server readiness check timed out on 127.0.0.1:17171."
    goto FAIL
)
call :log "[XMAGE] SERVIDOR LISTO en 127.0.0.1:17171"

rem ================================================================
rem 4/4 - Start the official launcher and verify its PID remains live.
rem The launcher receives its own stdout/stderr files. The sequential
rem log is never used as a child-process redirection target.
rem ================================================================
call :log "[4/4] Abriendo y verificando el lanzador oficial..."
call :control "Starting official launcher with UI scale 1.5."

set "XMAGE_JAVA=%JAVA%"
set "XMAGE_LAUNCHER=%LAUNCHER%"
set "XMAGE_ROOT=%ROOT%"
set "XMAGE_LIVE_LOG=%LAUNCHER_LIVE_LOG%"
set "XMAGE_LIVE_ERRORS_LOG=%LAUNCHER_LIVE_ERRORS_LOG%"
set "XMAGE_PID_FILE=%PID_FILE%"

rem Start-Process supplies a PID and redirects only to the two live logs.
rem [char]34 quotes the launcher path for Java without nesting cmd quotes.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';$javaArgs=@('-Dsun.java2d.uiScale=1.5','-jar',([char]34+$env:XMAGE_LAUNCHER+[char]34));$p=Start-Process -FilePath $env:XMAGE_JAVA -ArgumentList $javaArgs -WorkingDirectory $env:XMAGE_ROOT -RedirectStandardOutput $env:XMAGE_LIVE_LOG -RedirectStandardError $env:XMAGE_LIVE_ERRORS_LOG -PassThru;[IO.File]::WriteAllText($env:XMAGE_PID_FILE,[string]$p.Id)" 1>nul 2>>"%LAUNCHER_CONTROL_ERRORS_LOG%"
set "START_RC=!ERRORLEVEL!"
if not "!START_RC!"=="0" (
    call :log "ERROR: No se pudo iniciar el lanzador oficial."
    call :control_error "Start-Process returned exit code !START_RC!."
    goto FAIL
)

set "LAUNCHER_PID="
for /l %%N in (1,1,15) do (
    if not defined LAUNCHER_PID if exist "%PID_FILE%" set /p LAUNCHER_PID=<"%PID_FILE%"
    if defined LAUNCHER_PID (
        tasklist /fi "PID eq !LAUNCHER_PID!" 2>nul ^| findstr /i "java.exe" >nul 2>&1
        if not errorlevel 1 (
            set "LAUNCHER_VERIFIED=1"
            goto LAUNCHER_VERIFIED
        )
    )
    timeout /t 1 /nobreak >nul 2>&1
)

:LAUNCHER_VERIFIED
if not defined LAUNCHER_VERIFIED (
    call :log "ERROR: El lanzador oficial no permanecio vivo tras iniciar."
    call :control_error "Launcher PID was not verified as a live process."
    goto FAIL
)

call :control "Launcher PID verified as live: !LAUNCHER_PID!"
call :control "Only the official Launch Client button should be used."
call :log "LANZADOR OFICIAL ABIERTO Y VERIFICADO."
call :log "Pulsa solamente Launch Client en el lanzador oficial."
call :log "[XMAGE] Logs del launcher: !LAUNCHER_LIVE_LOG! y !LAUNCHER_LIVE_ERRORS_LOG!"
call :log "[XMAGE] Control: !LAUNCHER_CONTROL_LOG! y !LAUNCHER_CONTROL_ERRORS_LOG!"

if exist "%PID_FILE%" del /q "%PID_FILE%" >nul 2>&1
echo.
echo El lanzador oficial esta abierto y verificado.
echo Pulsa solamente "Launch Client".
echo.
pause
exit /b 0

:ROOT_ERROR
echo ERROR: No se encontro la instalacion preparada de XMage.
echo Debes colocar este .cmd en la carpeta raiz que contiene XMageLauncher-0.3.8.jar,
echo o mantener la ruta exacta del checkpoint:
echo %EXPECTED_ROOT%
pause
exit /b 2

:FAIL
if exist "%PID_FILE%" del /q "%PID_FILE%" >nul 2>&1
call :log "[XMAGE] Ejecucion detenida. Revisa el log secuencial y los logs de control."
echo.
echo La ejecucion se ha detenido. No se ha modificado la configuracion de XMage.
echo Revisa:
echo %SEQUENTIAL_LOG%
echo %LAUNCHER_CONTROL_ERRORS_LOG%
echo.
pause
exit /b 1

:log
>>"%SEQUENTIAL_LOG%" echo [!DATE! !TIME!] %~1
echo %~1
exit /b 0

:control
>>"%LAUNCHER_CONTROL_LOG%" echo [!DATE! !TIME!] %~1
exit /b 0

:control_error
>>"%LAUNCHER_CONTROL_ERRORS_LOG%" echo [!DATE! !TIME!] %~1
exit /b 0

:port_open
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$client=New-Object System.Net.Sockets.TcpClient;try{$client.Connect('127.0.0.1',17171);exit 0}catch{exit 1}" >nul 2>&1
exit /b !ERRORLEVEL!
