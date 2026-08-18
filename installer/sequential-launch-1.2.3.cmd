@echo off
setlocal EnableExtensions EnableDelayedExpansion

title XMage Community Patch RC1 1.4.61 - Sequential Launcher 1.2.3

rem ================================================================
rem XMage Community Patch RC1 1.4.61 - launcher 1.2.3
rem Safe incremental replacement for 1.2.2.
rem It does not rebuild, relink, or rewrite XMage configuration.
rem ================================================================

set "SCRIPT_VERSION=1.2.3"
set "ROOT=%~dp0"
set "EXPECTED_ROOT=J:\xmage repositorio\XMage-Community-Patch-hardening-update-architecture\tools\migration\XMage-Community-Patch-RC1-1.4.61-Official-Clone-v-1.2-CORE\XMage-Community-Patch-RC1-1.4.61-Official-Clone-v-1.2"

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

set "RUN_ID=%RANDOM%%RANDOM%"
set "SEQUENTIAL_LOG=%LOG_DIR%\sequential-launch-%RUN_ID%.log"
set "LAUNCHER_LIVE_LOG=%LOG_DIR%\launcher-live-%RUN_ID%.log"
set "LAUNCHER_LIVE_ERRORS_LOG=%LOG_DIR%\launcher-live-errors-%RUN_ID%.log"
set "LAUNCHER_CONTROL_LOG=%LOG_DIR%\launcher-control-%RUN_ID%.log"
set "LAUNCHER_CONTROL_ERRORS_LOG=%LOG_DIR%\launcher-control-errors-%RUN_ID%.log"
set "JAVA_VERSION_FILE=%TEMP%\xmage-java-version-%RUN_ID%.tmp"

>"%SEQUENTIAL_LOG%" echo [!DATE! !TIME!] Sequential launcher !SCRIPT_VERSION! started.
>"%LAUNCHER_CONTROL_LOG%" echo [!DATE! !TIME!] Launcher control started.
>"%LAUNCHER_CONTROL_ERRORS_LOG%" echo [!DATE! !TIME!] Launcher control errors.
>"%LAUNCHER_LIVE_LOG%" echo.
>"%LAUNCHER_LIVE_ERRORS_LOG%" echo.

call :log "[XMAGE] Script iniciado correctamente."
call :log "[XMAGE] Version: !SCRIPT_VERSION!"
call :log "[XMAGE] Log: !SEQUENTIAL_LOG!"
call :log "[XMAGE] UI blindada: -Dsun.java2d.uiScale=1.5"
call :control "Root: !ROOT!"
call :control "Java: !JAVA!"
call :control "Launcher: !LAUNCHER!"

rem 1/4 - Exact Java check.
"%JAVA%" -version >"%JAVA_VERSION_FILE%" 2>&1
findstr /c:"1.8.0_201" "%JAVA_VERSION_FILE%" >nul 2>&1
if errorlevel 1 (
    call :log "ERROR: No se ha verificado Java 8u201."
    call :control_error "Java 8u201 verification failed."
    goto FAIL
)
if exist "%JAVA_VERSION_FILE%" del /q "%JAVA_VERSION_FILE%" >nul 2>&1
call :log "[1/4] Java 8u201 detectado."

rem 2/4 - Existing server check.
call :log "[2/4] Comprobando el puerto 17171..."
call :port_open
if not errorlevel 1 (
    call :log "[XMAGE] El servidor ya esta escuchando. Se reutiliza."
    call :control "Server already listening on port 17171."
) else (
    call :log "[XMAGE] El servidor aun no responde; se esperara sin modificarlo."
    call :control "Waiting for prepared server on port 17171."
)

rem 3/4 - Active wait, without changing the server.
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
    call :log "ERROR: El servidor no esta disponible en 127.0.0.1:17171."
    call :control_error "Server readiness timed out."
    goto FAIL
)
call :log "[XMAGE] SERVIDOR LISTO en 127.0.0.1:17171"

rem 4/4 - Launch and verify the official launcher process.
call :log "[4/4] Abriendo y verificando el lanzador oficial..."
call :control "Starting launcher with UI scale 1.5."

start "" /b "%JAVA%" -Dsun.java2d.uiScale=1.5 -jar "%LAUNCHER%" 1>>"%LAUNCHER_LIVE_LOG%" 2>>"%LAUNCHER_LIVE_ERRORS_LOG%"
if errorlevel 1 (
    call :log "ERROR: Windows no pudo iniciar el lanzador oficial."
    call :control_error "The start command returned an error."
    goto FAIL
)

set "LAUNCHER_FOUND="
for /l %%N in (1,1,15) do (
    call :launcher_alive
    if not errorlevel 1 (
        set "LAUNCHER_FOUND=1"
        goto LAUNCHER_FOUND
    )
    timeout /t 1 /nobreak >nul 2>&1
)

:LAUNCHER_FOUND
if not defined LAUNCHER_FOUND (
    call :log "ERROR: No se encontro vivo el proceso del lanzador oficial."
    call :control_error "XMageLauncher-0.3.8.jar process was not found."
    goto FAIL
)

rem A second check avoids accepting a process that exits immediately.
timeout /t 2 /nobreak >nul 2>&1
call :launcher_alive
if errorlevel 1 (
    call :log "ERROR: El lanzador oficial se cerro inmediatamente."
    call :control_error "Launcher process exited during verification."
    goto FAIL
)

call :control "Official launcher process verified alive twice."
call :log "LANZADOR OFICIAL ABIERTO Y VERIFICADO."
call :log "Pulsa solamente Launch Client en el lanzador oficial."
call :log "[XMAGE] Logs del launcher: !LAUNCHER_LIVE_LOG! y !LAUNCHER_LIVE_ERRORS_LOG!"
call :log "[XMAGE] Control: !LAUNCHER_CONTROL_LOG! y !LAUNCHER_CONTROL_ERRORS_LOG!"

echo.
echo LANZADOR OFICIAL ABIERTO Y VERIFICADO.
echo Pulsa solamente "Launch Client".
echo.
pause
exit /b 0

:ROOT_ERROR
echo ERROR: No se encontro la instalacion preparada de XMage.
echo Coloca este archivo junto a XMageLauncher-0.3.8.jar o conserva la ruta:
echo %EXPECTED_ROOT%
pause
exit /b 2

:FAIL
if exist "%JAVA_VERSION_FILE%" del /q "%JAVA_VERSION_FILE%" >nul 2>&1
call :log "[XMAGE] Ejecucion detenida sin modificar la configuracion de XMage."
echo.
echo Ejecucion detenida. Revisa:
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
netstat -ano -p tcp 2>nul | findstr /c:":17171" | findstr /i "LISTENING" >nul 2>&1
exit /b !ERRORLEVEL!

:launcher_alive
powershell.exe -NoLogo -NoProfile -Command "$items=Get-CimInstance Win32_Process -Filter 'Name=''java.exe''';$alive=$false;foreach($item in $items){if($item.CommandLine -like '*XMageLauncher-0.3.8.jar*'){$alive=$true}};if($alive){exit 0}else{exit 1}" >nul 2>>"%LAUNCHER_CONTROL_ERRORS_LOG%"
exit /b !ERRORLEVEL!
