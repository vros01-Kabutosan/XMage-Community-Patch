@echo off
setlocal EnableExtensions EnableDelayedExpansion
title XMage RC1.3 - RESCATE VISUAL v1.4

set "RESULT=1"
goto :MAIN

:MAIN
set "SCRIPT_DIR=%~dp0"
set "LOG_ROOT=J:\mtg\_LOGS"
set "ACTIVE_ROOT=J:\mtg\xmage"
set "STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "STAMP=%STAMP: =0%"
set "LOG_DIR=%LOG_ROOT%\smoke_trigger_RESCATE_v1.4_%STAMP%"
set "SMOKE_ROOT=J:\mtg\_SMOKE\trigger-RESCATE-v1.4_%STAMP%"
set "CLIENT_ROOT=%SMOKE_ROOT%\mage-client"
set "SERVER_ROOT=%SMOKE_ROOT%\mage-server"
set "TRANSCRIPT=%LOG_DIR%\smoke_transcript.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%SMOKE_ROOT%" mkdir "%SMOKE_ROOT%"
call :LOG "START RESCATE VISUAL v1.4"
call :LOG "Script=%~f0"

set "REPO_ROOT="
for %%R in ("J:\xmage repositorio\XMage-Community-Patch-git" "J:\xmage repositorio\XMage-Community-Patch") do if not defined REPO_ROOT if exist "%%~R\source\xmage\1.4.61V1-community-patch-v-1\pom.xml" set "REPO_ROOT=%%~R"
if not defined REPO_ROOT for %%A in ("%SCRIPT_DIR%..\..") do if exist "%%~fA\source\xmage\1.4.61V1-community-patch-v-1\pom.xml" set "REPO_ROOT=%%~fA"
if not defined REPO_ROOT call :FAIL "No se encontro el clon de fuente RC1.3."

set "SOURCE_ROOT=%REPO_ROOT%\source\xmage\1.4.61V1-community-patch-v-1"
set "CLIENT_MODULE=%SOURCE_ROOT%\Mage.Client"
set "COMMON_MODULE=%SOURCE_ROOT%\Mage.Common"
call :LOG "Repository=%REPO_ROOT%"
call :LOG "Source=%SOURCE_ROOT%"
if not exist "%SOURCE_ROOT%\pom.xml" call :FAIL "Falta el POM raiz."
if not exist "%CLIENT_MODULE%\pom.xml" call :FAIL "Falta Mage.Client."
if not exist "%COMMON_MODULE%\pom.xml" call :FAIL "Falta Mage.Common."

set "JAVA_CMD="
for %%J in ("C:\Program Files\BellSoft\LibericaJDK-17\bin\java.exe" "C:\Program Files\Eclipse Adoptium\jdk-17\bin\java.exe" "C:\Program Files\Java\jdk-17\bin\java.exe") do if not defined JAVA_CMD if exist "%%~J" set "JAVA_CMD=%%~J"
if not defined JAVA_CMD for /f "delims=" %%J in ('where java.exe 2^>nul') do if not defined JAVA_CMD set "JAVA_CMD=%%J"
if not defined JAVA_CMD call :FAIL "No se encontro Java."
for %%J in ("%JAVA_CMD%") do set "JAVA_BIN=%%~dpJ"
set "PATH=%JAVA_BIN%;%PATH%"
"%JAVA_CMD%" -version > "%LOG_DIR%\java_version.log" 2>&1
call :LOG "Java=%JAVA_CMD%"

call :LOG "Localizando distribucion activa funcional sin modificarla."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $c=Get-ChildItem -LiteralPath '%ACTIVE_ROOT%' -Filter 'mage-client-1.4.61.jar' -File -Recurse | Select-Object -First 1; $s=Get-ChildItem -LiteralPath '%ACTIVE_ROOT%' -Filter 'mage-server-1.4.61.jar' -File -Recurse | Select-Object -First 1; if(!$c -or !$s){exit 1}; $c.Directory.Parent.FullName | Set-Content -Encoding ASCII '%LOG_DIR%\active_client_root.txt'; $s.Directory.Parent.FullName | Set-Content -Encoding ASCII '%LOG_DIR%\active_server_root.txt'; $c.FullName | Set-Content -Encoding ASCII '%LOG_DIR%\active_client_jar.txt'; $s.FullName | Set-Content -Encoding ASCII '%LOG_DIR%\active_server_jar.txt'" > "%LOG_DIR%\active_discovery.log" 2>&1
if errorlevel 1 call :FAIL "No se localizaron cliente y servidor 1.4.61 en la instalacion activa."
set /p "ACTIVE_CLIENT_ROOT="<"%LOG_DIR%\active_client_root.txt"
set /p "ACTIVE_SERVER_ROOT="<"%LOG_DIR%\active_server_root.txt"
call :LOG "Active client=%ACTIVE_CLIENT_ROOT%"
call :LOG "Active server=%ACTIVE_SERVER_ROOT%"
if not exist "%ACTIVE_CLIENT_ROOT%\lib\mage-client-1.4.61.jar" call :FAIL "La raiz activa del cliente no es valida."
if not exist "%ACTIVE_SERVER_ROOT%\lib\mage-server-1.4.61.jar" call :FAIL "La raiz activa del servidor no es valida."

set "MVN_CMD="
for %%M in ("J:\tools\apache-maven-3.8.8\bin\mvn.cmd" "J:\mtg\tools\apache-maven-3.8.8\bin\mvn.cmd" "C:\Program Files\Apache Maven\bin\mvn.cmd") do if not defined MVN_CMD if exist "%%~M" set "MVN_CMD=%%~M"
if not defined MVN_CMD for /f "delims=" %%M in ('where mvn.cmd 2^>nul') do if not defined MVN_CMD set "MVN_CMD=%%M"
if not defined MVN_CMD (
  set "MAVEN_HOME=%TEMP%\apache-maven-3.8.8"
  if not exist "!MAVEN_HOME!\bin\mvn.cmd" (
    call :LOG "Descargando Apache Maven 3.8.8."
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $z=Join-Path $env:TEMP 'apache-maven-3.8.8-bin.zip'; Invoke-WebRequest -UseBasicParsing -Uri 'https://archive.apache.org/dist/maven/maven-3/3.8.8/binaries/apache-maven-3.8.8-bin.zip' -OutFile $z; Expand-Archive -LiteralPath $z -DestinationPath $env:TEMP -Force" > "%LOG_DIR%\maven_download.log" 2>&1
    if errorlevel 1 call :FAIL "No se pudo descargar Maven 3.8.8."
  )
  if exist "!MAVEN_HOME!\bin\mvn.cmd" set "MVN_CMD=!MAVEN_HOME!\bin\mvn.cmd"
)
if not defined MVN_CMD call :FAIL "No se pudo preparar Maven."
"%MVN_CMD%" -version > "%LOG_DIR%\maven_version.log" 2>&1
if errorlevel 1 call :FAIL "Maven no puede ejecutarse."

call :LOG "Compilando solo Mage.Client y dependencias necesarias."
pushd "%SOURCE_ROOT%"
"%MVN_CMD%" -DskipTests package -pl Mage.Client -am > "%LOG_DIR%\maven_stdout.log" 2> "%LOG_DIR%\maven_stderr.log"
set "MAVEN_RC=!ERRORLEVEL!"
popd
call :LOG "Maven exit code=!MAVEN_RC!"
if not "!MAVEN_RC!"=="0" call :FAIL "La compilacion del cliente fallo."

set "NEW_CLIENT_JAR=%CLIENT_MODULE%\target\mage-client-1.4.61.jar"
set "NEW_COMMON_JAR=%COMMON_MODULE%\target\mage-common-1.4.61.jar"
if not exist "%NEW_CLIENT_JAR%" call :FAIL "No se genero mage-client-1.4.61.jar."
if not exist "%NEW_COMMON_JAR%" call :FAIL "No se genero mage-common-1.4.61.jar."
certutil -hashfile "%NEW_CLIENT_JAR%" SHA256 > "%LOG_DIR%\new_client_sha256.log" 2>&1
certutil -hashfile "%NEW_COMMON_JAR%" SHA256 > "%LOG_DIR%\new_common_sha256.log" 2>&1

call :LOG "Clonando distribuciones funcionales. No se usa MIR."
robocopy "%ACTIVE_SERVER_ROOT%" "%SERVER_ROOT%" /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ /NFL /NDL /NP /LOG:"%LOG_DIR%\copy_server.log"
set "ROBO_SERVER=!ERRORLEVEL!"
if !ROBO_SERVER! GEQ 8 call :FAIL "Fallo al clonar el servidor activo."
robocopy "%ACTIVE_CLIENT_ROOT%" "%CLIENT_ROOT%" /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ /NFL /NDL /NP /XD "%ACTIVE_CLIENT_ROOT%\plugins\images" /LOG:"%LOG_DIR%\copy_client.log"
set "ROBO_CLIENT=!ERRORLEVEL!"
if !ROBO_CLIENT! GEQ 8 call :FAIL "Fallo al clonar el cliente activo."

if exist "%ACTIVE_CLIENT_ROOT%\plugins\images" (
  if not exist "%CLIENT_ROOT%\plugins" mkdir "%CLIENT_ROOT%\plugins"
  mklink /J "%CLIENT_ROOT%\plugins\images" "%ACTIVE_CLIENT_ROOT%\plugins\images" > "%LOG_DIR%\images_link.log" 2>&1
  if errorlevel 1 call :LOG "AVISO: no se pudo crear el enlace de imagenes."
)

if not exist "%CLIENT_ROOT%\lib\mage-client-1.4.61.jar" call :FAIL "El clon no contiene el JAR del cliente."
if not exist "%CLIENT_ROOT%\lib\mage-common-1.4.61.jar" call :FAIL "El clon del cliente no contiene mage-common."
if not exist "%SERVER_ROOT%\lib\mage-common-1.4.61.jar" call :FAIL "El clon del servidor no contiene mage-common."
if not exist "%SERVER_ROOT%\lib\mage-server-1.4.61.jar" call :FAIL "El clon no contiene el JAR del servidor."

copy /Y "%NEW_CLIENT_JAR%" "%CLIENT_ROOT%\lib\mage-client-1.4.61.jar" > "%LOG_DIR%\overlay_client.log" 2>&1
if errorlevel 1 call :FAIL "No se pudo aplicar el JAR nuevo del cliente."
copy /Y "%NEW_COMMON_JAR%" "%CLIENT_ROOT%\lib\mage-common-1.4.61.jar" > "%LOG_DIR%\overlay_common_client.log" 2>&1
if errorlevel 1 call :FAIL "No se pudo aplicar mage-common al cliente."
copy /Y "%NEW_COMMON_JAR%" "%SERVER_ROOT%\lib\mage-common-1.4.61.jar" > "%LOG_DIR%\overlay_common_server.log" 2>&1
if errorlevel 1 call :FAIL "No se pudo aplicar mage-common al servidor."
call :LOG "Overlay aplicado solo dentro del clon smoke."

powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=Get-NetTCPConnection -LocalPort 17171 -State Listen -ErrorAction SilentlyContinue; if($c){$c | Format-List | Out-String | Set-Content -Encoding UTF8 '%LOG_DIR%\port_before.log'; exit 1}else{exit 0}" >nul 2>&1
if errorlevel 1 call :FAIL "El puerto 17171 ya esta ocupado."

call :LOG "Arrancando servidor estable clonado."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $p=Start-Process -FilePath '%JAVA_CMD%' -WorkingDirectory '%SERVER_ROOT%' -ArgumentList @('-Xmx4G','-Dfile.encoding=UTF-8','-jar','.\lib\mage-server-1.4.61.jar') -RedirectStandardOutput '%LOG_DIR%\server_stdout.log' -RedirectStandardError '%LOG_DIR%\server_stderr.log' -PassThru; $p.Id | Set-Content -Encoding ascii '%LOG_DIR%\server_pid.txt'" > "%LOG_DIR%\server_start.log" 2>&1
if errorlevel 1 call :FAIL "No se pudo crear el proceso del servidor."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$end=(Get-Date).AddSeconds(120); $ok=$false; while((Get-Date) -lt $end){$c=Get-NetTCPConnection -LocalPort 17171 -State Listen -ErrorAction SilentlyContinue; if($c){$c | Format-List | Out-String | Set-Content -Encoding UTF8 '%LOG_DIR%\port_after.log'; $ok=$true; break}; Start-Sleep -Seconds 1}; if($ok){exit 0}else{exit 1}" > "%LOG_DIR%\server_wait.log" 2>&1
if errorlevel 1 call :FAIL "El servidor no abrio 17171."
call :LOG "SERVIDOR VERIFICADO: 17171."

call :LOG "Arrancando cliente modificado del clon."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $p=Start-Process -FilePath '%JAVA_CMD%' -WorkingDirectory '%CLIENT_ROOT%' -ArgumentList @('-Xmx4G','-Dsun.java2d.uiScale=1.5','-Dfile.encoding=UTF-8','-jar','.\lib\mage-client-1.4.61.jar') -RedirectStandardOutput '%LOG_DIR%\client_stdout.log' -RedirectStandardError '%LOG_DIR%\client_stderr.log' -PassThru; $p.Id | Set-Content -Encoding ascii '%LOG_DIR%\client_pid.txt'" > "%LOG_DIR%\client_start.log" 2>&1
if errorlevel 1 call :FAIL "No se pudo crear el proceso del cliente."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$targetId=[int](Get-Content '%LOG_DIR%\client_pid.txt'); $end=(Get-Date).AddSeconds(120); $ok=$false; while((Get-Date) -lt $end){$p=Get-Process -Id $targetId -ErrorAction SilentlyContinue; if($p -and ($p.MainWindowHandle -ne 0 -or $p.MainWindowTitle -like '*XMage*')){$p | Select-Object Id,ProcessName,MainWindowHandle,MainWindowTitle | Format-List | Out-String | Set-Content -Encoding UTF8 '%LOG_DIR%\xmage_window.log'; $ok=$true; break}; if(!$p){break}; Start-Sleep -Seconds 2}; if($ok){exit 0}else{exit 1}" > "%LOG_DIR%\client_wait.log" 2>&1
if errorlevel 1 call :FAIL "El cliente no creo una ventana XMage real."

call :LOG "SMOKE VISUAL: CLIENTE ABIERTO Y SERVIDOR VERIFICADO."
call :LOG "Smoke=%SMOKE_ROOT%"
call :LOG "Logs=%LOG_DIR%"
echo.
echo CLIENTE ABIERTO. COMPRUEBA EL INDICADOR ROJO EN UNA PARTIDA.
echo No se ha modificado J:\mtg\xmage.
echo.
pause
exit /b 0

:FAIL
call :LOG "ERROR: %~1"
echo.
echo SMOKE VISUAL: FALLIDO
echo LOG: %LOG_DIR%
echo El proceso se detiene aqui.
echo.
pause
exit

:LOG
>> "%TRANSCRIPT%" echo [%DATE% %TIME%] %~1
echo %~1
exit /b 0
