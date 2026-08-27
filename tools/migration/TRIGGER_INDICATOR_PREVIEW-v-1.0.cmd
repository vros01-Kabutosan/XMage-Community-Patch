@echo off
setlocal EnableExtensions EnableDelayedExpansion
title XMage - Trigger Indicator Preview

set "RESULT=1"
goto :MAIN

:MAIN
set "LOG_ROOT=J:\mtg\_LOGS"
set "ACTIVE_ROOT=J:\mtg\xmage"
set "STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "STAMP=%STAMP: =0%"
set "LOG_DIR=%LOG_ROOT%\trigger_preview_v1.0_%STAMP%"
set "PREVIEW_ROOT=J:\mtg\_SMOKE\trigger-preview-v1.0_%STAMP%"
set "TRANSCRIPT=%LOG_DIR%\preview_transcript.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%PREVIEW_ROOT%" mkdir "%PREVIEW_ROOT%"
call :LOG "START Trigger Indicator Preview v1.0"

set "REPO_ROOT="
for %%R in ("J:\xmage repositorio\XMage-Community-Patch-git" "J:\xmage repositorio\XMage-Community-Patch") do if not defined REPO_ROOT if exist "%%~R\source\xmage\1.4.61V1-community-patch-v-1\pom.xml" set "REPO_ROOT=%%~R"
if not defined REPO_ROOT call :FAIL "No se encontro el clon de fuente RC1.3."
set "SOURCE_ROOT=%REPO_ROOT%\source\xmage\1.4.61V1-community-patch-v-1"
set "CLIENT_MODULE=%SOURCE_ROOT%\Mage.Client"
set "COMMON_MODULE=%SOURCE_ROOT%\Mage.Common"
call :LOG "Source=%SOURCE_ROOT%"

set "JAVA_CMD="
for %%J in ("C:\Program Files\BellSoft\LibericaJDK-17\bin\java.exe" "C:\Program Files\Eclipse Adoptium\jdk-17\bin\java.exe") do if not defined JAVA_CMD if exist "%%~J" set "JAVA_CMD=%%~J"
if not defined JAVA_CMD for /f "delims=" %%J in ('where java.exe 2^>nul') do if not defined JAVA_CMD set "JAVA_CMD=%%J"
if not defined JAVA_CMD call :FAIL "No se encontro Java."
for %%J in ("%JAVA_CMD%") do set "JAVA_BIN=%%~dpJ"
set "PATH=%JAVA_BIN%;%PATH%"
"%JAVA_CMD%" -version > "%LOG_DIR%\java_version.log" 2>&1

set "MVN_CMD="
for %%M in ("J:\tools\apache-maven-3.8.8\bin\mvn.cmd" "J:\mtg\tools\apache-maven-3.8.8\bin\mvn.cmd") do if not defined MVN_CMD if exist "%%~M" set "MVN_CMD=%%~M"
if not defined MVN_CMD for /f "delims=" %%M in ('where mvn.cmd 2^>nul') do if not defined MVN_CMD set "MVN_CMD=%%M"
if defined MVN_CMD goto :MAVEN_READY
set "MAVEN_HOME=%TEMP%\apache-maven-3.8.8"
if exist "%MAVEN_HOME%\bin\mvn.cmd" set "MVN_CMD=%MAVEN_HOME%\bin\mvn.cmd"
if defined MVN_CMD goto :MAVEN_READY
call :LOG "Descargando Apache Maven 3.8.8."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $z=Join-Path $env:TEMP 'apache-maven-3.8.8-bin.zip'; Invoke-WebRequest -UseBasicParsing -Uri 'https://archive.apache.org/dist/maven/maven-3/3.8.8/binaries/apache-maven-3.8.8-bin.zip' -OutFile $z; Expand-Archive -LiteralPath $z -DestinationPath $env:TEMP -Force" > "%LOG_DIR%\maven_download.log" 2>&1
if errorlevel 1 call :FAIL "No se pudo descargar Maven."
if not exist "%MAVEN_HOME%\bin\mvn.cmd" call :FAIL "Maven no quedo disponible tras la descarga."
set "MVN_CMD=%MAVEN_HOME%\bin\mvn.cmd"

:MAVEN_READY
"%MVN_CMD%" -version > "%LOG_DIR%\maven_version.log" 2>&1
if errorlevel 1 call :FAIL "Maven no puede ejecutarse."
call :LOG "Compilando cliente y Mage.Common."
pushd "%SOURCE_ROOT%"
"%MVN_CMD%" -DskipTests package -pl Mage.Client -am > "%LOG_DIR%\maven_stdout.log" 2> "%LOG_DIR%\maven_stderr.log"
set "MAVEN_RC=!ERRORLEVEL!"
popd
if not "!MAVEN_RC!"=="0" call :FAIL "La compilacion fallo. Ver maven_stdout.log y maven_stderr.log."
set "NEW_CLIENT_JAR=%CLIENT_MODULE%\target\mage-client-1.4.61.jar"
set "NEW_COMMON_JAR=%COMMON_MODULE%\target\mage-common-1.4.61.jar"
if not exist "%NEW_CLIENT_JAR%" call :FAIL "No se genero mage-client-1.4.61.jar."
if not exist "%NEW_COMMON_JAR%" call :FAIL "No se genero mage-common-1.4.61.jar."

call :LOG "Localizando cliente activo solo para lectura de librerias e imagenes."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $c=Get-ChildItem -LiteralPath '%ACTIVE_ROOT%' -Filter 'mage-client-*.jar' -File -Recurse | Where-Object {$_.Name -notmatch 'sources|javadoc|tests' -and $_.Directory.Name -eq 'lib'} | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if(!$c){exit 1}; $c.Directory.Parent.FullName | Set-Content -Encoding ASCII '%LOG_DIR%\active_client_root.txt'" > "%LOG_DIR%\active_discovery.log" 2>&1
if errorlevel 1 call :FAIL "No se localizo el cliente activo."
set /p "ACTIVE_CLIENT_ROOT="<"%LOG_DIR%\active_client_root.txt"
if not exist "%ACTIVE_CLIENT_ROOT%\lib" call :FAIL "La raiz del cliente activo no es valida."
call :LOG "Active client=%ACTIVE_CLIENT_ROOT%"

mkdir "%PREVIEW_ROOT%\plugins" >nul 2>&1
robocopy "%ACTIVE_CLIENT_ROOT%\plugins" "%PREVIEW_ROOT%\plugins" *.jar /R:1 /W:1 /NFL /NDL /NP /LOG:"%LOG_DIR%\copy_plugins.log"
set "PLUGIN_RC=!ERRORLEVEL!"
if !PLUGIN_RC! GEQ 8 call :FAIL "No se pudieron copiar los plugins del cliente."
if exist "%ACTIVE_CLIENT_ROOT%\plugins\images" (
  mklink /J "%PREVIEW_ROOT%\plugins\images" "%ACTIVE_CLIENT_ROOT%\plugins\images" > "%LOG_DIR%\images_link.log" 2>&1
  if errorlevel 1 call :LOG "AVISO: no se pudo enlazar images; el dialogo puede usar marcadores."
)

call :LOG "Abriendo cliente en modo de previsualizacion."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $cp='%NEW_CLIENT_JAR%;%NEW_COMMON_JAR%;%ACTIVE_CLIENT_ROOT%\lib\*;%PREVIEW_ROOT%\plugins\*'; $args=@('-Xmx4G','-Dsun.java2d.uiScale=1.5','-Dfile.encoding=UTF-8','-Duser.home=%PREVIEW_ROOT%\home','-cp',$cp,'mage.client.MageFrame','-triggerIndicatorPreview'); $p=Start-Process -FilePath '%JAVA_CMD%' -WorkingDirectory '%PREVIEW_ROOT%' -ArgumentList $args -RedirectStandardOutput '%LOG_DIR%\client_stdout.log' -RedirectStandardError '%LOG_DIR%\client_stderr.log' -PassThru; $p.Id | Set-Content -Encoding ASCII '%LOG_DIR%\client_pid.txt'" > "%LOG_DIR%\client_start.log" 2>&1
if errorlevel 1 call :FAIL "No se pudo iniciar el cliente de previsualizacion."

powershell -NoProfile -ExecutionPolicy Bypass -Command "$targetId=[int](Get-Content '%LOG_DIR%\client_pid.txt'); $end=(Get-Date).AddSeconds(120); $ok=$false; while((Get-Date) -lt $end){$p=Get-Process -Id $targetId -ErrorAction SilentlyContinue; if($p -and ($p.MainWindowHandle -ne 0 -or $p.MainWindowTitle -like '*XMage*')){$p | Select-Object Id,ProcessName,MainWindowHandle,MainWindowTitle | Format-List | Out-String | Set-Content -Encoding UTF8 '%LOG_DIR%\xmage_window.log'; $ok=$true; break}; if(!$p){break}; Start-Sleep -Seconds 2}; if($ok){exit 0}else{exit 1}" > "%LOG_DIR%\client_wait.log" 2>&1
if errorlevel 1 call :FAIL "El cliente no abrio una ventana XMage. Revisar client_stdout.log y client_stderr.log."

call :LOG "PREVIEW ABIERTA: el primer permanente del dialogo debe mostrar la exclamacion roja."
echo.
echo PREVIEW ABIERTA. MIRA EL PRIMER PERMANENTE DEL DIALOGO.
echo No se ha iniciado servidor ni modificado J:\mtg\xmage.
echo LOG: %LOG_DIR%
echo.
pause
exit /b 0

:FAIL
call :LOG "ERROR: %~1"
echo.
echo PREVIEW: FALLIDA
echo LOG: %LOG_DIR%
echo.
pause
exit

:LOG
>> "%TRANSCRIPT%" echo [%DATE% %TIME%] %~1
echo %~1
exit /b 0
