@echo off
setlocal EnableExtensions EnableDelayedExpansion
title XMage RC1.3 - Trigger Visual Smoke FINAL v1.3

set "RESULT=1"
goto :MAIN

:MAIN
set "SCRIPT_DIR=%~dp0"
set "LOG_ROOT=J:\mtg\_LOGS"
set "ACTIVE_ROOT=J:\mtg\xmage"
set "STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "STAMP=%STAMP: =0%"
set "LOG_DIR=%LOG_ROOT%\smoke_visual_RC1.3_FINAL_v1.3_%STAMP%"
set "SMOKE_ROOT=J:\mtg\_SMOKE\RC1.3-trigger-FINAL-v1.3_%STAMP%"
set "SERVER_ROOT=%SMOKE_ROOT%\server"
set "CLIENT_ROOT=%SMOKE_ROOT%\client"
set "TRANSCRIPT=%LOG_DIR%\smoke_transcript.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%SMOKE_ROOT%" mkdir "%SMOKE_ROOT%"
call :log "START smoke visual RC1.3 FINAL"
call :log "Script=%~f0"

set "REPO_ROOT="
for %%R in ("J:\xmage repositorio\XMage-Community-Patch-git" "J:\xmage repositorio\XMage-Community-Patch" "J:\mtg\_ARCHIVO\RC1.3-WORK-PILE") do if not defined REPO_ROOT if exist "%%~R\source\xmage\1.4.61V1-community-patch-v-1\pom.xml" set "REPO_ROOT=%%~R"
if not defined REPO_ROOT for %%A in ("%SCRIPT_DIR%..\..") do if exist "%%~fA\source\xmage\1.4.61V1-community-patch-v-1\pom.xml" set "REPO_ROOT=%%~fA"

if not defined REPO_ROOT (
  call :abort "No se encontro el clon aislado de XMage RC1.3."
)
set "SOURCE_ROOT=%REPO_ROOT%\source\xmage\1.4.61V1-community-patch-v-1"
set "SERVER_MODULE=%SOURCE_ROOT%\Mage.Server"
set "CLIENT_MODULE=%SOURCE_ROOT%\Mage.Client"
call :log "Repository=%REPO_ROOT%"
call :log "Source=%SOURCE_ROOT%"

if not exist "%SOURCE_ROOT%\pom.xml" call :abort "No se encuentra el POM raiz."
if not exist "%SERVER_MODULE%\pom.xml" call :abort "No se encuentra Mage.Server."
if not exist "%CLIENT_MODULE%\pom.xml" call :abort "No se encuentra Mage.Client."

set "JAVA_CMD="
for %%J in ("C:\Program Files\BellSoft\LibericaJDK-17\bin\java.exe" "C:\Program Files\Eclipse Adoptium\jdk-17\bin\java.exe" "C:\Program Files\Java\jdk-17\bin\java.exe") do if not defined JAVA_CMD if exist "%%~J" set "JAVA_CMD=%%~J"
if not defined JAVA_CMD for /f "delims=" %%J in ('where java.exe 2^>nul') do if not defined JAVA_CMD set "JAVA_CMD=%%J"
if not defined JAVA_CMD call :abort "No se encontro Java."
for %%J in ("%JAVA_CMD%") do set "JAVA_BIN=%%~dpJ"
set "PATH=%JAVA_BIN%;%PATH%"
"%JAVA_CMD%" -version > "%LOG_DIR%\java_version.log" 2>&1
call :log "Java=%JAVA_CMD%"

set "SERVER_ZIP="
set "CLIENT_ZIP="
if exist "%SERVER_MODULE%\target" for /r "%SERVER_MODULE%\target" %%F in (mage-server-*.zip) do if not defined SERVER_ZIP set "SERVER_ZIP=%%~fF"
if exist "%CLIENT_MODULE%\target" for /r "%CLIENT_MODULE%\target" %%F in (mage-client-*.zip) do if not defined CLIENT_ZIP set "CLIENT_ZIP=%%~fF"

if defined SERVER_ZIP if defined CLIENT_ZIP (
  call :log "Distribuciones Assembly existentes; se reutilizan sin recompilar."
) else (
  call :log "No existen ambas distribuciones Assembly. Se preparara Maven automaticamente."
  set "MVN_CMD="
  for %%M in ("J:\tools\apache-maven-3.8.8\bin\mvn.cmd" "J:\mtg\tools\apache-maven-3.8.8\bin\mvn.cmd" "C:\Program Files\Apache Maven\bin\mvn.cmd") do if not defined MVN_CMD if exist "%%~M" set "MVN_CMD=%%~M"
  if not defined MVN_CMD for /f "delims=" %%M in ('where mvn.cmd 2^>nul') do if not defined MVN_CMD set "MVN_CMD=%%M"
  if not defined MVN_CMD (
    set "MAVEN_HOME=%TEMP%\apache-maven-3.8.8"
    if not exist "!MAVEN_HOME!\bin\mvn.cmd" (
      call :log "Maven no esta disponible. Descargando Apache Maven 3.8.8."
      powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $z=Join-Path $env:TEMP 'apache-maven-3.8.8-bin.zip'; Invoke-WebRequest -UseBasicParsing -Uri 'https://archive.apache.org/dist/maven/maven-3/3.8.8/binaries/apache-maven-3.8.8-bin.zip' -OutFile $z; Expand-Archive -LiteralPath $z -DestinationPath $env:TEMP -Force" > "%LOG_DIR%\maven_download.log" 2>&1
      if errorlevel 1 call :abort "No se pudo descargar Maven 3.8.8."
    )
    if exist "!MAVEN_HOME!\bin\mvn.cmd" set "MVN_CMD=!MAVEN_HOME!\bin\mvn.cmd"
  )
  if not defined MVN_CMD call :abort "No se pudo localizar ni preparar Maven."
  "%MVN_CMD%" -version > "%LOG_DIR%\maven_version.log" 2>&1
  if errorlevel 1 call :abort "Maven no puede ejecutarse."
  call :log "Compilando Mage.Server y Mage.Client con Assembly."
  pushd "%SOURCE_ROOT%"
  "%MVN_CMD%" -DskipTests package assembly:single -pl Mage.Server,Mage.Client -am > "%LOG_DIR%\maven_stdout.log" 2> "%LOG_DIR%\maven_stderr.log"
  set "MAVEN_RC=!ERRORLEVEL!"
  popd
  call :log "Maven exit code=!MAVEN_RC!"
  if not "!MAVEN_RC!"=="0" call :abort "La compilacion Assembly fallo. Revisar maven_stdout.log y maven_stderr.log."
  set "SERVER_ZIP="
  set "CLIENT_ZIP="
  for /r "%SERVER_MODULE%\target" %%F in (mage-server-*.zip) do if not defined SERVER_ZIP set "SERVER_ZIP=%%~fF"
  for /r "%CLIENT_MODULE%\target" %%F in (mage-client-*.zip) do if not defined CLIENT_ZIP set "CLIENT_ZIP=%%~fF"
  if not defined SERVER_ZIP call :abort "La compilacion termino pero no genero ZIP de servidor."
  if not defined CLIENT_ZIP call :abort "La compilacion termino pero no genero ZIP de cliente."
)

call :log "Server ZIP=%SERVER_ZIP%"
call :log "Client ZIP=%CLIENT_ZIP%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Expand-Archive -LiteralPath '%SERVER_ZIP%' -DestinationPath '%SERVER_ROOT%' -Force" > "%LOG_DIR%\extract_server.log" 2>&1
if errorlevel 1 call :abort "No se pudo extraer la distribucion del servidor."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Expand-Archive -LiteralPath '%CLIENT_ZIP%' -DestinationPath '%CLIENT_ROOT%' -Force" > "%LOG_DIR%\extract_client.log" 2>&1
if errorlevel 1 call :abort "No se pudo extraer la distribucion del cliente."

set "SERVER_JAR="
set "CLIENT_JAR="
for %%F in ("%SERVER_ROOT%\lib\mage-server-*.jar") do if not defined SERVER_JAR set "SERVER_JAR=%%~fF"
for %%F in ("%CLIENT_ROOT%\lib\mage-client-*.jar") do if not defined CLIENT_JAR set "CLIENT_JAR=%%~fF"
if not defined SERVER_JAR call :abort "Falta el JAR del servidor en server\lib."
if not defined CLIENT_JAR call :abort "Falta el JAR del cliente en client\lib."
if not exist "%SERVER_ROOT%\config\config.xml" call :abort "Falta server\config\config.xml."
if not exist "%SERVER_ROOT%\plugins" call :abort "Falta server\plugins."
if not exist "%CLIENT_ROOT%\plugins" mkdir "%CLIENT_ROOT%\plugins"

if exist "%ACTIVE_ROOT%\plugins\images" (
  mklink /J "%CLIENT_ROOT%\plugins\images" "%ACTIVE_ROOT%\plugins\images" > "%LOG_DIR%\images_link.log" 2>&1
  if errorlevel 1 call :log "AVISO: no se pudo enlazar images; la instalacion activa no fue modificada."
  if not errorlevel 1 call :log "Imagenes enlazadas en modo lectura desde la instalacion activa."
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=Get-NetTCPConnection -LocalPort 17171 -State Listen -ErrorAction SilentlyContinue; if($c){$c | Format-List | Out-String | Set-Content -Encoding UTF8 '%LOG_DIR%\port_before.log'; exit 1}else{exit 0}" >nul 2>&1
if errorlevel 1 call :abort "El puerto 17171 ya esta ocupado. No se mata ningun proceso automaticamente."

call :log "Distribucion verificada. Server JAR=%SERVER_JAR%"
call :log "Distribucion verificada. Client JAR=%CLIENT_JAR%"
call :log "Arrancando servidor desde su raiz de distribucion."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $p=Start-Process -FilePath '%JAVA_CMD%' -WorkingDirectory '%SERVER_ROOT%' -ArgumentList @('-Xmx4G','-Dfile.encoding=UTF-8','-jar','.\lib\mage-server-1.4.61.jar') -RedirectStandardOutput '%LOG_DIR%\server_stdout.log' -RedirectStandardError '%LOG_DIR%\server_stderr.log' -PassThru -WindowStyle Normal; $p.Id | Set-Content -Encoding ascii '%LOG_DIR%\server_pid.txt'; if(!$p){exit 1}" > "%LOG_DIR%\server_start.log" 2>&1
if errorlevel 1 call :abort "No se pudo crear el proceso del servidor."

call :log "Esperando al servidor y verificando que 17171 pertenezca a un proceso activo."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$end=(Get-Date).AddSeconds(90); $ok=$false; while((Get-Date) -lt $end){$c=Get-NetTCPConnection -LocalPort 17171 -State Listen -ErrorAction SilentlyContinue; if($c){$c | Format-List | Out-String | Set-Content -Encoding UTF8 '%LOG_DIR%\port_after.log'; $ok=$true; break}; Start-Sleep -Seconds 1}; if($ok){exit 0}else{exit 1}" > "%LOG_DIR%\server_wait.log" 2>&1
if errorlevel 1 call :abort "El servidor no abrio el puerto 17171. Revisar server_stdout.log y server_stderr.log."
call :log "SERVIDOR VERIFICADO: 17171 escuchando."

call :log "Arrancando cliente visible desde su raiz de distribucion."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $p=Start-Process -FilePath '%JAVA_CMD%' -WorkingDirectory '%CLIENT_ROOT%' -ArgumentList @('-Xmx4G','-Dsun.java2d.uiScale=1.5','-Dfile.encoding=UTF-8','-jar','.\lib\mage-client-1.4.61.jar') -RedirectStandardOutput '%LOG_DIR%\client_stdout.log' -RedirectStandardError '%LOG_DIR%\client_stderr.log' -PassThru -WindowStyle Normal; $p.Id | Set-Content -Encoding ascii '%LOG_DIR%\client_pid.txt'; if(!$p){exit 1}" > "%LOG_DIR%\client_start.log" 2>&1
if errorlevel 1 call :abort "No se pudo crear el proceso del cliente."

call :log "Esperando el proceso Java del cliente y una ventana XMage real."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$targetId=[int](Get-Content '%LOG_DIR%\client_pid.txt'); $end=(Get-Date).AddSeconds(120); $ok=$false; while((Get-Date) -lt $end){$p=Get-Process -Id $targetId -ErrorAction SilentlyContinue; if($p -and ($p.MainWindowHandle -ne 0 -or $p.MainWindowTitle -like '*XMage*')){$p | Select-Object Id,ProcessName,MainWindowHandle,MainWindowTitle | Format-List | Out-String | Set-Content -Encoding UTF8 '%LOG_DIR%\xmage_window.log'; $ok=$true; break}; if(!$p){break}; Start-Sleep -Seconds 2}; if($ok){exit 0}else{exit 1}" > "%LOG_DIR%\client_window_wait.log" 2>&1
tasklist /FI "IMAGENAME eq java.exe" /FO LIST > "%LOG_DIR%\java_processes_after_start.log" 2>&1
if errorlevel 1 (
  call :abort "El cliente Java no creo una ventana XMage verificable. Revisar client_stdout.log, client_stderr.log y client_window_wait.log."
)

call :log "SMOKE VISUAL: CLIENTE ABIERTO Y SERVIDOR VERIFICADO."
call :log "El cliente queda abierto para la comprobacion visual del indicador rojo."
call :log "Logs=%LOG_DIR%"
call :log "Smoke root=%SMOKE_ROOT%"
set "RESULT=0"
goto :FINISH

:ABORT
set "RESULT=1"
call :log "ERROR: %~1"
echo.
echo SMOKE VISUAL: FALLIDO
echo LOG: %LOG_DIR%
echo.
echo El proceso se detiene aqui. No se ejecutaran fases posteriores.
pause
exit /b 1

:LOG
>> "%TRANSCRIPT%" echo [%DATE% %TIME%] %~1
echo %~1
exit /b 0

:FINISH
echo.
if "%RESULT%"=="0" (
  echo SMOKE VISUAL: CLIENTE ABIERTO Y SERVIDOR VERIFICADO
) else (
  echo SMOKE VISUAL: FALLIDO
)
echo LOG: %LOG_DIR%
echo.
pause
exit /b %RESULT%
