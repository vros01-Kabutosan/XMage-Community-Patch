@echo off
setlocal EnableExtensions EnableDelayedExpansion
title XMage RC1.3 - Activar indicador T - v-1.0.1

set "REPO_URL=https://github.com/vros01-Kabutosan/XMage-Community-Patch.git"
set "BRANCH=work/rc1.3-v-1.2.13-trigger-indicator"
set "REQUIRED_ANCESTOR_COMMIT=50c58509d561be356fede9d481094282210bbcd5"
set "ACTIVE_ROOT=J:\mtg\xmage"
set "LOG_ROOT=J:\mtg\_LOGS"
set "ARCHIVE_ROOT=J:\mtg\_ARCHIVO"
set "STAMP="
for /f "delims=" %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%T"
if not defined STAMP set "STAMP=manual"
set "LOG_DIR=%LOG_ROOT%\activate_T_RC1.3-v-1.0.1_%STAMP%"
set "STAGE_ROOT=J:\mtg\_SMOKE\activate_T_RC1.3-v-1.0.1_%STAMP%"
set "SOURCE_REPO=%STAGE_ROOT%\source-repository"
set "SOURCE_ROOT=%SOURCE_REPO%\source\rc1.1-complete-community"
set "BACKUP_DIR=%ARCHIVE_ROOT%\trigger-indicator-before-activation_%STAMP%"
set "TRANSCRIPT=%LOG_DIR%\activation_transcript.log"
set "INSTALL_STARTED=0"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%STAGE_ROOT%" mkdir "%STAGE_ROOT%"
call :LOG "START activacion automatica del indicador T"
call :LOG "Rama fuente=%BRANCH%"
call :LOG "Commit base minimo exigido=%REQUIRED_ANCESTOR_COMMIT%"
call :LOG "Instalacion objetivo=%ACTIVE_ROOT%"

set "GIT_CMD="
for /f "delims=" %%G in ('where git.exe 2^>nul') do if not defined GIT_CMD set "GIT_CMD=%%G"
if defined GIT_CMD goto GIT_READY
call :LOG "Git no encontrado: descarga automatica de Git portatil en TEMP."
set "GIT_CACHE=%TEMP%\xmage-tools\mingit"
if not exist "%GIT_CACHE%" mkdir "%GIT_CACHE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $r=Invoke-RestMethod -UseBasicParsing -Uri 'https://api.github.com/repos/git-for-windows/git/releases/latest'; $a=$null; foreach($x in $r.assets){if($x.name -match '^MinGit-.*-64-bit\.zip$'){$a=$x;break}}; if($null -eq $a){throw 'No se encontro MinGit x64'}; $z=Join-Path $env:TEMP 'xmage-tools\mingit.zip'; Invoke-WebRequest -UseBasicParsing -Uri $a.browser_download_url -OutFile $z; Expand-Archive -LiteralPath $z -DestinationPath (Join-Path $env:TEMP 'xmage-tools\mingit') -Force" > "%LOG_DIR%\git_download.log" 2>&1
if errorlevel 1 goto FAIL_GIT_DOWNLOAD
if exist "%GIT_CACHE%\cmd\git.exe" set "GIT_CMD=%GIT_CACHE%\cmd\git.exe"
:GIT_READY
if not defined GIT_CMD goto FAIL_GIT
"%GIT_CMD%" --version > "%LOG_DIR%\git_where.log" 2>&1
if errorlevel 1 goto FAIL_GIT

if not exist "%ACTIVE_ROOT%" goto FAIL_ACTIVE

call :LOG "Clonando la candidata blindada en staging aislado."
"%GIT_CMD%" clone --single-branch --branch "%BRANCH%" "%REPO_URL%" "%SOURCE_REPO%" > "%LOG_DIR%\git_clone.log" 2>&1
if errorlevel 1 goto FAIL_CLONE
if not exist "%SOURCE_ROOT%\pom.xml" goto FAIL_SOURCE
"%GIT_CMD%" -C "%SOURCE_REPO%" rev-parse HEAD > "%LOG_DIR%\source_commit.log" 2>&1
if errorlevel 1 goto FAIL_SOURCE
for /f "usebackq delims=" %%P in ("%LOG_DIR%\source_commit.log") do if not defined SOURCE_COMMIT set "SOURCE_COMMIT=%%P"
if /i "%SOURCE_COMMIT%"=="%REQUIRED_ANCESTOR_COMMIT%" goto SOURCE_COMMIT_OK
"%GIT_CMD%" -C "%SOURCE_REPO%" merge-base --is-ancestor "%REQUIRED_ANCESTOR_COMMIT%" "%SOURCE_COMMIT%" > "%LOG_DIR%\source_ancestry.log" 2>&1
if errorlevel 1 goto FAIL_SOURCE_COMMIT
:SOURCE_COMMIT_OK
call :LOG "Clonado y revision de la base confirmados."

set "JAVA_CMD="
set "JAVA_PATH_FILE=%LOG_DIR%\java_path.txt"
del /q "%JAVA_PATH_FILE%" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $c=@(); $roots=@('C:\Program Files\BellSoft','C:\Program Files\Eclipse Adoptium','C:\Program Files\Java'); foreach($r in $roots){if(Test-Path -LiteralPath $r){foreach($d in (Get-ChildItem -LiteralPath $r -Directory -ErrorAction SilentlyContinue)){if($d.Name -match '17'){$c += Join-Path $d.FullName 'bin\java.exe'}}}}; $c += @(where.exe java.exe 2>$null); foreach($p in $c){if(Test-Path -LiteralPath $p){$v=(& $p -version 2>&1) -join [Environment]::NewLine; if($v -match 'version \"17\.'){[IO.File]::WriteAllText('%JAVA_PATH_FILE%',$p); break}}}" > "%LOG_DIR%\java_detection.log" 2>&1
if exist "%JAVA_PATH_FILE%" set /p "JAVA_CMD="<"%JAVA_PATH_FILE%"
if defined JAVA_CMD goto JAVA_READY
call :LOG "JDK 17 no encontrado: descarga automatica de Temurin 17 en TEMP."
set "JDK_CACHE=%TEMP%\xmage-tools\jdk17"
if not exist "%JDK_CACHE%" mkdir "%JDK_CACHE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $z=Join-Path $env:TEMP 'xmage-tools\temurin17.zip'; Invoke-WebRequest -UseBasicParsing -Uri 'https://api.adoptium.net/v3/binary/latest/17/ga/windows/x64/jdk/hotspot/normal/eclipse?project=jdk' -OutFile $z; Expand-Archive -LiteralPath $z -DestinationPath (Join-Path $env:TEMP 'xmage-tools\jdk17') -Force" > "%LOG_DIR%\jdk_download.log" 2>&1
if errorlevel 1 goto FAIL_JAVA_DOWNLOAD
powershell -NoProfile -ExecutionPolicy Bypass -Command "foreach($f in (Get-ChildItem -LiteralPath '%JDK_CACHE%' -Recurse -File -Filter java.exe -ErrorAction SilentlyContinue)){[IO.File]::WriteAllText('%JAVA_PATH_FILE%',$f.FullName);break}" > "%LOG_DIR%\jdk_path.log" 2>&1
if exist "%JAVA_PATH_FILE%" set /p "JAVA_CMD="<"%JAVA_PATH_FILE%"
:JAVA_READY
if not defined JAVA_CMD goto FAIL_JAVA
"%JAVA_CMD%" -version > "%LOG_DIR%\java_version.log" 2>&1
findstr /c:"17." "%LOG_DIR%\java_version.log" >nul
if errorlevel 1 goto FAIL_JAVA
for %%J in ("%JAVA_CMD%") do set "JAVA_BIN=%%~dpJ"
set "PATH=%JAVA_BIN%;%PATH%"
call :LOG "JDK 17 confirmado."

set "MVN_CMD="
for %%M in (
    "J:\tools\apache-maven-3.8.8\bin\mvn.cmd"
    "J:\mtg\tools\apache-maven-3.8.8\bin\mvn.cmd"
    "%TEMP%\apache-maven-3.8.8\bin\mvn.cmd"
) do if not defined MVN_CMD if exist "%%~M" set "MVN_CMD=%%~M"
if not defined MVN_CMD for /f "delims=" %%M in ('where mvn.cmd 2^>nul') do if not defined MVN_CMD set "MVN_CMD=%%M"
if defined MVN_CMD goto MAVEN_READY
call :LOG "Maven no encontrado: descarga automatica de Apache Maven 3.8.8."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $z=Join-Path $env:TEMP 'apache-maven-3.8.8-bin.zip'; Invoke-WebRequest -UseBasicParsing -Uri 'https://archive.apache.org/dist/maven/maven-3/3.8.8/binaries/apache-maven-3.8.8-bin.zip' -OutFile $z; Expand-Archive -LiteralPath $z -DestinationPath $env:TEMP -Force" > "%LOG_DIR%\maven_download.log" 2>&1
if errorlevel 1 goto FAIL_MAVEN_DOWNLOAD
if exist "%TEMP%\apache-maven-3.8.8\bin\mvn.cmd" set "MVN_CMD=%TEMP%\apache-maven-3.8.8\bin\mvn.cmd"
:MAVEN_READY
if not defined MVN_CMD goto FAIL_MAVEN
call "%MVN_CMD%" -version > "%LOG_DIR%\maven_version.log" 2>&1
if errorlevel 1 goto FAIL_MAVEN
call :LOG "Maven confirmado."

call :LOG "Compilando Mage.Client y dependencias desde la candidata blindada."
pushd "%SOURCE_ROOT%"
call "%MVN_CMD%" -DskipTests package -pl Mage.Client -am > "%LOG_DIR%\maven_full.log" 2>&1
set "BUILD_RC=!ERRORLEVEL!"
popd
type "%LOG_DIR%\maven_full.log"
if not "%BUILD_RC%"=="0" goto FAIL_BUILD

set "NEW_CLIENT=%SOURCE_ROOT%\Mage.Client\target\mage-client-1.4.61.jar"
set "NEW_COMMON=%SOURCE_ROOT%\Mage.Common\target\mage-common-1.4.61.jar"
if not exist "%NEW_CLIENT%" goto FAIL_CLIENT_JAR
if not exist "%NEW_COMMON%" goto FAIL_COMMON_JAR
call :LOG "Compilacion correcta y JARs generados."

call :LOG "Localizando exactamente los JARs activos del cliente."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $root='J:\mtg\xmage'; $clients=@(); foreach($f in (Get-ChildItem -LiteralPath $root -Recurse -File -Filter 'mage-client-*.jar' -ErrorAction Stop)){if($f.Name -match '^mage-client-[0-9].*\.jar$'){$clients+=$f}}; $candidates=@(); $clientLibs=@(); foreach($f in $clients){$d=$f.Directory; $lib=$null; while($null -ne $d -and $null -eq $lib){if($d.Name -ieq 'lib'){$lib=$d;break};$child=Join-Path $d.FullName 'lib'; if(Test-Path -LiteralPath $child){$lib=Get-Item -LiteralPath $child;break};$d=$d.Parent}; if($null -ne $lib){$seen=$false; foreach($u in $candidates){if($u.FullName -eq $f.FullName){$seen=$true;break}}; if(-not $seen){$candidates+=$f;$clientLibs+=$lib}}}; if($candidates.Count -ne 1){throw ('Se esperaba 1 cliente activo y se encontraron '+$candidates.Count)}; $client=$candidates[0]; $clientLib=$clientLibs[0]; $commons=@(); foreach($f in (Get-ChildItem -LiteralPath $clientLib.FullName -File -Filter 'mage-common-*.jar' -ErrorAction Stop)){$commons+=$f}; if($commons.Count -ne 1){throw ('En la biblioteca del cliente se esperaban 1 mage-common y se encontraron '+$commons.Count)}; Set-Content -LiteralPath '%LOG_DIR%\active_client_jar.txt' -Value $client.FullName -Encoding ASCII; Set-Content -LiteralPath '%LOG_DIR%\active_common_jar.txt' -Value $commons[0].FullName -Encoding ASCII; Set-Content -LiteralPath '%LOG_DIR%\active_client_lib.txt' -Value $clientLib.FullName -Encoding ASCII; 'CLIENT='+$client.FullName; 'CLIENT_LIB='+$clientLib.FullName; 'COMMON='+$commons[0].FullName" > "%LOG_DIR%\active_discovery.log" 2>&1
if errorlevel 1 goto FAIL_DISCOVERY
set "ACTIVE_CLIENT_JAR="
set "ACTIVE_COMMON_JAR="
for /f "usebackq delims=" %%P in ("%LOG_DIR%\active_client_jar.txt") do if not defined ACTIVE_CLIENT_JAR set "ACTIVE_CLIENT_JAR=%%P"
for /f "usebackq delims=" %%P in ("%LOG_DIR%\active_common_jar.txt") do if not defined ACTIVE_COMMON_JAR set "ACTIVE_COMMON_JAR=%%P"
if not exist "%ACTIVE_CLIENT_JAR%" goto FAIL_DISCOVERY
if not exist "%ACTIVE_COMMON_JAR%" goto FAIL_DISCOVERY
call :LOG "Cliente activo=%ACTIVE_CLIENT_JAR%"
call :LOG "Common activo=%ACTIVE_COMMON_JAR%"

call :LOG "Cerrando solo procesos Java que utilizan la instalacion XMage objetivo."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root='J:\mtg\xmage'; $procs=@(); foreach($p in (Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)){if($p.Name -in @('java.exe','javaw.exe') -and $p.CommandLine -and $p.CommandLine.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0){$procs+=$p}}; foreach($p in $procs){Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop; 'STOPPED '+$p.ProcessId+' '+$p.Name}" > "%LOG_DIR%\stop_xmage_processes.log" 2>&1
if errorlevel 1 goto FAIL_STOP

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
if not exist "%BACKUP_DIR%\." goto FAIL_BACKUP
call :LOG "Origen JAR cliente=%ACTIVE_CLIENT_JAR%"
call :LOG "Origen JAR common=%ACTIVE_COMMON_JAR%"
call :LOG "Destino backup=%BACKUP_DIR%"
if not exist "%ACTIVE_CLIENT_JAR%" goto FAIL_BACKUP
if not exist "%ACTIVE_COMMON_JAR%" goto FAIL_BACKUP
call :LOG "Creando backup previo antes de sustituir los JARs."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Copy-Item -LiteralPath '%ACTIVE_CLIENT_JAR%' -Destination '%BACKUP_DIR%\mage-client-before.jar' -Force; if(-not (Test-Path -LiteralPath '%BACKUP_DIR%\mage-client-before.jar')){throw 'No se creo el backup del cliente'}" > "%LOG_DIR%\backup_client.log" 2>&1
if errorlevel 1 goto FAIL_BACKUP
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Copy-Item -LiteralPath '%ACTIVE_COMMON_JAR%' -Destination '%BACKUP_DIR%\mage-common-before.jar' -Force; if(-not (Test-Path -LiteralPath '%BACKUP_DIR%\mage-common-before.jar')){throw 'No se creo el backup de common'}" > "%LOG_DIR%\backup_common.log" 2>&1
if errorlevel 1 goto FAIL_BACKUP
set "INSTALL_STARTED=1"

call :LOG "Buscando una JAR anterior valida para conservar los recursos graficos del cliente."
set "RESOURCE_SOURCE_FILE=%LOG_DIR%\resource_source.txt"
del /q "%RESOURCE_SOURCE_FILE%" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Add-Type -AssemblyName System.IO.Compression; Add-Type -AssemblyName System.IO.Compression.FileSystem; $required=@('menu/preferences.png','menu/connect.png'); $candidates=@('%ACTIVE_CLIENT_JAR%'); $ar='J:\mtg\_ARCHIVO'; if(Test-Path -LiteralPath $ar){$candidates += @(Get-ChildItem -LiteralPath $ar -Directory -Filter 'trigger-indicator-before-activation_*' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | ForEach-Object {Join-Path $_.FullName 'mage-client-before.jar'})}; foreach($p in $candidates){if(-not (Test-Path -LiteralPath $p)){continue}; $z=$null; try{$z=[IO.Compression.ZipFile]::OpenRead($p); $names=@($z.Entries | ForEach-Object {$_.FullName}); $ok=$true; foreach($r in $required){if($names -notcontains $r){$ok=$false;break}}; if($ok){Set-Content -LiteralPath '%RESOURCE_SOURCE_FILE%' -Value $p -Encoding ASCII; 'RESOURCE_SOURCE='+$p; break}}finally{if($null -ne $z){$z.Dispose()}}}; if(-not (Test-Path -LiteralPath '%RESOURCE_SOURCE_FILE%')){throw 'No se encontro una JAR anterior con menu/preferences.png y menu/connect.png'}" > "%LOG_DIR%\resource_source.log" 2>&1
if errorlevel 1 goto FAIL_RESOURCE_MERGE
set "RESOURCE_SOURCE_JAR="
for /f "usebackq delims=" %%P in ("%RESOURCE_SOURCE_FILE%") do if not defined RESOURCE_SOURCE_JAR set "RESOURCE_SOURCE_JAR=%%P"
if not defined RESOURCE_SOURCE_JAR goto FAIL_RESOURCE_MERGE
if not exist "%RESOURCE_SOURCE_JAR%" goto FAIL_RESOURCE_MERGE
call :LOG "JAR de recursos=%RESOURCE_SOURCE_JAR%"
call :LOG "Conservando recursos graficos anteriores que no estan versionados en la fuente."
set "MERGED_CLIENT=%STAGE_ROOT%\mage-client-1.4.61-merged.jar"
copy /b /y "%NEW_CLIENT%" "%MERGED_CLIENT%" > "%LOG_DIR%\resource_merge_copy.log" 2>&1
if errorlevel 1 goto FAIL_RESOURCE_MERGE
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Add-Type -AssemblyName System.IO.Compression; Add-Type -AssemblyName System.IO.Compression.FileSystem; $old=[IO.Compression.ZipFile]::OpenRead('%RESOURCE_SOURCE_JAR%'); $tmp='%STAGE_ROOT%\mage-client-1.4.61-merged.tmp.jar'; Copy-Item -LiteralPath '%MERGED_CLIENT%' -Destination $tmp -Force; $new=[IO.Compression.ZipFile]::Open($tmp,[IO.Compression.ZipArchiveMode]::Update); $names=New-Object 'System.Collections.Generic.HashSet[string]'; foreach($e in $new.Entries){[void]$names.Add($e.FullName)}; $added=0; foreach($e in $old.Entries){if(-not $names.Contains($e.FullName)){ $ne=$new.CreateEntry($e.FullName); $i=$e.Open(); $o=$ne.Open(); try{$i.CopyTo($o)}finally{$o.Dispose();$i.Dispose()}; [void]$names.Add($e.FullName); $added++ }}; $new.Dispose(); $old.Dispose(); Move-Item -LiteralPath $tmp -Destination '%MERGED_CLIENT%' -Force; 'MISSING_RESOURCES_RESTORED='+$added" > "%LOG_DIR%\resource_merge.log" 2>&1
if errorlevel 1 goto FAIL_RESOURCE_MERGE
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Add-Type -AssemblyName System.IO.Compression; Add-Type -AssemblyName System.IO.Compression.FileSystem; $z=[IO.Compression.ZipFile]::OpenRead('%MERGED_CLIENT%'); $names=@($z.Entries | ForEach-Object {$_.FullName}); $z.Dispose(); if($names -notcontains 'menu/preferences.png'){throw 'Falta menu/preferences.png en el JAR final'}; if($names -notcontains 'menu/connect.png'){throw 'Falta menu/connect.png en el JAR final'}; 'REQUIRED_MENU_RESOURCES=OK'" > "%LOG_DIR%\resource_verify.log" 2>&1
if errorlevel 1 goto FAIL_RESOURCE_MERGE
set "NEW_CLIENT=%MERGED_CLIENT%"
call :LOG "Recursos del cliente anterior conservados y JAR final preparado."

call :LOG "Instalando los dos JARs compilados en la instalacion activa."
copy /b /y "%NEW_CLIENT%" "%ACTIVE_CLIENT_JAR%" > "%LOG_DIR%\install_client.log" 2>&1
if errorlevel 1 goto FAIL_INSTALL
copy /b /y "%NEW_COMMON%" "%ACTIVE_COMMON_JAR%" > "%LOG_DIR%\install_common.log" 2>&1
if errorlevel 1 goto FAIL_INSTALL

powershell -NoProfile -ExecutionPolicy Bypass -Command "$a=(Get-FileHash -LiteralPath '%NEW_CLIENT%' -Algorithm SHA256).Hash; $b=(Get-FileHash -LiteralPath '%ACTIVE_CLIENT_JAR%' -Algorithm SHA256).Hash; $c=(Get-FileHash -LiteralPath '%NEW_COMMON%' -Algorithm SHA256).Hash; $d=(Get-FileHash -LiteralPath '%ACTIVE_COMMON_JAR%' -Algorithm SHA256).Hash; 'CLIENT_SOURCE='+$a; 'CLIENT_ACTIVE='+$b; 'COMMON_SOURCE='+$c; 'COMMON_ACTIVE='+$d; if($a -ne $b -or $c -ne $d){exit 1}" > "%LOG_DIR%\sha256_verification.log" 2>&1
if errorlevel 1 goto FAIL_VERIFY
call :LOG "PASS: JARs instalados y SHA-256 verificados."
call :LOG "Backup=%BACKUP_DIR%"
call :LOG "LOG=%LOG_DIR%"
echo.
echo ACTIVACION COMPLETADA CORRECTAMENTE.
echo El indicador T ya esta instalado en XMage.
echo Inicia XMage con tu lanzador habitual.
echo Backup: %BACKUP_DIR%
echo Logs: %LOG_DIR%
echo.
pause
exit /b 0

:FAIL_GIT
call :FAIL "Git no esta disponible en PATH."
exit /b 1
:FAIL_GIT_DOWNLOAD
call :FAIL "No se pudo descargar Git portatil automaticamente. No se modifico nada."
exit /b 1
:FAIL_ACTIVE
call :FAIL "No se encontro J:\mtg\xmage. No se modifico nada."
exit /b 1
:FAIL_CLONE
call :FAIL "No se pudo descargar la rama estable fusionada."
exit /b 1
:FAIL_SOURCE
call :FAIL "La fuente candidata no contiene el POM esperado en source\rc1.1-complete-community."
exit /b 1
:FAIL_SOURCE_COMMIT
call :FAIL "El clon no coincide con el commit candidato blindado. No se modifico nada."
exit /b 1
:FAIL_JAVA
call :FAIL "Se requiere JDK 17 y no se localizo uno valido. No se modifico nada."
exit /b 1
:FAIL_JAVA_DOWNLOAD
call :FAIL "No se pudo descargar JDK 17 automaticamente. No se modifico nada."
exit /b 1
:FAIL_MAVEN_DOWNLOAD
call :FAIL "No se pudo descargar Maven 3.8.8 automaticamente. No se modifico nada."
exit /b 1
:FAIL_MAVEN
call :FAIL "Maven no esta disponible o no puede ejecutarse. No se modifico nada."
exit /b 1
:FAIL_BUILD
call :FAIL "La compilacion fallo. No se modifico nada. Revisar maven_full.log."
exit /b 1
:FAIL_CLIENT_JAR
call :FAIL "No se genero mage-client-1.4.61.jar. No se modifico nada."
exit /b 1
:FAIL_COMMON_JAR
call :FAIL "No se genero mage-common-1.4.61.jar. No se modifico nada."
exit /b 1
:FAIL_RESOURCE_MERGE
call :FAIL "No se pudieron conservar los recursos graficos del cliente anterior. No se modifico nada."
exit /b 1
:FAIL_DISCOVERY
call :FAIL "La deteccion de la instalacion activa no fue univoca. No se modifico nada."
exit /b 1
:FAIL_STOP
call :FAIL "No se pudieron cerrar los procesos XMage de forma controlada. No se modifico nada."
exit /b 1
:FAIL_BACKUP
call :FAIL "No se pudo crear el backup previo. No se modifico nada."
exit /b 1
:FAIL_INSTALL
call :FAIL "Fallo la instalacion de los JARs. Se intentara restaurar el backup."
exit /b 1
:FAIL_VERIFY
call :FAIL "La verificacion SHA-256 fallo. Se restaurara el backup."
exit /b 1

:FAIL
call :LOG "FAIL: %~1"
if "%INSTALL_STARTED%"=="1" (
    call :LOG "ROLLBACK: restaurando los JARs desde el backup."
    copy /b /y "%BACKUP_DIR%\mage-client-before.jar" "%ACTIVE_CLIENT_JAR%" > "%LOG_DIR%\rollback_client.log" 2>&1
    copy /b /y "%BACKUP_DIR%\mage-common-before.jar" "%ACTIVE_COMMON_JAR%" > "%LOG_DIR%\rollback_common.log" 2>&1
)
echo.
echo ACTIVACION FALLIDA. NO SE ENTREGA COMO EXITOSA.
echo %~1
echo Logs: %LOG_DIR%
if exist "%BACKUP_DIR%" echo Backup: %BACKUP_DIR%
echo.
pause
exit /b 1

:LOG
>>"%TRANSCRIPT%" echo [%DATE% %TIME%] %~1
echo %~1
exit /b 0
