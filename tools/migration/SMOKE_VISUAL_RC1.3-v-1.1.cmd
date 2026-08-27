@echo off
setlocal EnableExtensions EnableDelayedExpansion
title XMage RC1.3 - Trigger Visual Smoke v1.1

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT="
for %%R in ("J:\xmage repositorio\XMage-Community-Patch-git" "J:\xmage repositorio\XMage-Community-Patch" "J:\mtg\_ARCHIVO\RC1.3-WORK-PILE") do if not defined REPO_ROOT if exist "%%~R\source\xmage\1.4.61V1-community-patch-v-1\pom.xml" set "REPO_ROOT=%%~R"
if not defined REPO_ROOT for %%A in ("%SCRIPT_DIR%..\..") do if exist "%%~fA\source\xmage\1.4.61V1-community-patch-v-1\pom.xml" set "REPO_ROOT=%%~fA"
set "SOURCE_ROOT=%REPO_ROOT%\source\xmage\1.4.61V1-community-patch-v-1"
set "SERVER_MODULE=%SOURCE_ROOT%\Mage.Server"
set "CLIENT_MODULE=%SOURCE_ROOT%\Mage.Client"
set "LOG_ROOT=J:\mtg\_LOGS"
set "ACTIVE_ROOT=J:\mtg\xmage"
set "STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "STAMP=%STAMP: =0%"
set "LOG_DIR=%LOG_ROOT%\smoke_visual_RC1.3_v1.1_%STAMP%"
set "SMOKE_ROOT=J:\mtg\_SMOKE\RC1.3-trigger-v1.1_%STAMP%"
set "SERVER_ROOT=%SMOKE_ROOT%\server"
set "CLIENT_ROOT=%SMOKE_ROOT%\client"
set "TRANSCRIPT=%LOG_DIR%\smoke_transcript.log"
set "RESULT=1"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%SMOKE_ROOT%" mkdir "%SMOKE_ROOT%"
call :log "START smoke visual RC1.3 v1.1"
call :log "Repository=%REPO_ROOT%"
call :log "Source=%SOURCE_ROOT%"
call :log "Smoke=%SMOKE_ROOT%"

if not exist "%SOURCE_ROOT%\pom.xml" (
  call :fail "No se encuentra el POM raiz: %SOURCE_ROOT%\pom.xml"
  goto :finish
)
if not exist "%SERVER_MODULE%\pom.xml" (
  call :fail "No se encuentra Mage.Server"
  goto :finish
)
if not exist "%CLIENT_MODULE%\pom.xml" (
  call :fail "No se encuentra Mage.Client"
  goto :finish
)
if not exist "%ACTIVE_ROOT%" call :log "AVISO: no existe la instalacion activa; se continuara sin copiar enlaces de imagenes."

where java > "%LOG_DIR%\java_where.log" 2>&1
if errorlevel 1 (
  call :fail "Java no esta disponible en PATH."
  goto :finish
)
java -version > "%LOG_DIR%\java_version.log" 2>&1
where mvn > "%LOG_DIR%\maven_where.log" 2>&1
if errorlevel 1 (
  call :fail "Maven no esta disponible en PATH."
  goto :finish
)
mvn -version > "%LOG_DIR%\maven_version.log" 2>&1
call :log "Java y Maven detectados. Consulta los logs de versiones."

call :log "Compilando distribuciones Assembly de servidor y cliente."
pushd "%SOURCE_ROOT%"
mvn -DskipTests package assembly:single -pl Mage.Server,Mage.Client -am > "%LOG_DIR%\maven_stdout.log" 2> "%LOG_DIR%\maven_stderr.log"
set "MAVEN_RC=%ERRORLEVEL%"
popd
call :log "Maven exit code=%MAVEN_RC%"
if not "%MAVEN_RC%"=="0" (
  call :fail "La compilacion Assembly ha fallado. Revisar maven_stdout.log y maven_stderr.log."
  goto :finish
)

set "SERVER_ZIP="
set "CLIENT_ZIP="
for /r "%SERVER_MODULE%\target" %%F in (mage-server*.zip) do if not defined SERVER_ZIP set "SERVER_ZIP=%%~fF"
for /r "%CLIENT_MODULE%\target" %%F in (mage-client*.zip) do if not defined CLIENT_ZIP set "CLIENT_ZIP=%%~fF"
if not defined SERVER_ZIP (
  call :fail "No se encontro la distribucion ZIP del servidor."
  goto :finish
)
if not defined CLIENT_ZIP (
  call :fail "No se encontro la distribucion ZIP del cliente."
  goto :finish
)
call :log "Server ZIP=%SERVER_ZIP%"
call :log "Client ZIP=%CLIENT_ZIP%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%SERVER_ZIP%' -DestinationPath '%SERVER_ROOT%' -Force" > "%LOG_DIR%\extract_server.log" 2>&1
if errorlevel 1 (
  call :fail "No se pudo extraer la distribucion del servidor."
  goto :finish
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%CLIENT_ZIP%' -DestinationPath '%CLIENT_ROOT%' -Force" > "%LOG_DIR%\extract_client.log" 2>&1
if errorlevel 1 (
  call :fail "No se pudo extraer la distribucion del cliente."
  goto :finish
)

if not exist "%SERVER_ROOT%\lib\mage-server-1.4.61.jar" (
  call :fail "Falta server\lib\mage-server-1.4.61.jar."
  goto :finish
)
if not exist "%SERVER_ROOT%\config\config.xml" (
  call :fail "Falta server\config\config.xml."
  goto :finish
)
if not exist "%CLIENT_ROOT%\lib\mage-client-1.4.61.jar" (
  call :fail "Falta client\lib\mage-client-1.4.61.jar."
  goto :finish
)
call :log "Distribuciones completas verificadas."

if exist "%ACTIVE_ROOT%\plugins\images" (
  if not exist "%CLIENT_ROOT%\plugins" mkdir "%CLIENT_ROOT%\plugins"
  mklink /J "%CLIENT_ROOT%\plugins\images" "%ACTIVE_ROOT%\plugins\images" > "%LOG_DIR%\images_link.log" 2>&1
  if errorlevel 1 call :log "AVISO: no se pudo crear enlace de imagenes; no se modifico la instalacion activa."
  if not errorlevel 1 call :log "Enlace de imagenes creado solo desde smoke hacia instalacion activa."
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-NetTCPConnection -LocalPort 17171 -State Listen -ErrorAction SilentlyContinue; if($p){$p | Format-List | Out-String | Set-Content -Encoding UTF8 '%LOG_DIR%\port_before.log'; exit 1}else{exit 0}" >nul 2>&1
if not errorlevel 1 goto :port_free
call :fail "El puerto 17171 ya esta ocupado. No se matan procesos automaticamente."
goto :finish
:port_free

call :log "Arrancando servidor real desde server\ con mage-server-1.4.61.jar."
pushd "%SERVER_ROOT%"
start "XMAGE-RC1.3-SERVER-SMOKE" /D "%SERVER_ROOT%" cmd /c ""java" -Xmx4G -Dfile.encoding=UTF-8 -jar ".\lib\mage-server-1.4.61.jar" 1>"%LOG_DIR%\server_stdout.log" 2>"%LOG_DIR%\server_stderr.log""
set "SERVER_START_RC=%ERRORLEVEL%"
popd
call :log "Server start command exit code=%SERVER_START_RC%"

call :log "Esperando confirmacion real de 17171."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; 1..60 | %% { if(Get-NetTCPConnection -LocalPort 17171 -State Listen -ErrorAction SilentlyContinue){$ok=$true;break}; Start-Sleep -Seconds 1 }; if($ok){exit 0}else{exit 1}" > "%LOG_DIR%\server_wait.log" 2>&1
if errorlevel 1 (
  call :fail "El servidor no ha abierto 17171. Revisar server_stdout.log y server_stderr.log."
  goto :finish
)
call :log "SERVIDOR VERIFICADO: 17171 escuchando."

call :log "Arrancando cliente visible desde client\ con mage-client-1.4.61.jar."
pushd "%CLIENT_ROOT%"
start "XMAGE-RC1.3-CLIENT-SMOKE" /D "%CLIENT_ROOT%" cmd /c ""java" -Xmx4G -Dsun.java2d.uiScale=1.5 -Dfile.encoding=UTF-8 -jar ".\lib\mage-client-1.4.61.jar" 1>"%LOG_DIR%\client_stdout.log" 2>"%LOG_DIR%\client_stderr.log""
set "CLIENT_START_RC=%ERRORLEVEL%"
popd
call :log "Client start command exit code=%CLIENT_START_RC%"

timeout /t 12 /nobreak >nul
tasklist /FI "IMAGENAME eq java.exe" /FO LIST > "%LOG_DIR%\java_processes_after_start.log" 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=Get-Process | ? {$_.MainWindowTitle -like '*XMage*'}; if($w){$w | Select-Object Id,ProcessName,MainWindowTitle | Format-List | Out-String | Set-Content -Encoding UTF8 '%LOG_DIR%\xmage_window.log'; exit 0}else{exit 1}" >nul 2>&1
if errorlevel 1 (
  call :fail "El cliente no presenta una ventana XMage verificable. Revisar client_stdout.log y client_stderr.log."
  goto :finish
)

call :log "SMOKE VISUAL: CLIENTE ABIERTO Y SERVIDOR VERIFICADO."
call :log "El cliente queda abierto para comprobacion manual del indicador rojo."
call :log "Logs=%LOG_DIR%"
call :log "Smoke root=%SMOKE_ROOT%"
set "RESULT=0"
goto :finish

:fail
call :log "ERROR: %~1"
set "RESULT=1"
exit /b 0

:log
>> "%TRANSCRIPT%" echo [%DATE% %TIME%] %~1
echo %~1
exit /b 0

:finish
if "%RESULT%"=="0" (
  echo.
  echo SMOKE VISUAL: CLIENTE ABIERTO Y SERVIDOR VERIFICADO
) else (
  echo.
  echo SMOKE VISUAL: FALLIDO
)
echo LOG: %LOG_DIR%
echo.
pause
exit /b %RESULT%
