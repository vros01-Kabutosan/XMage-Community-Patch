[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RecoveryRoot,
    [Parameter(Mandatory = $true)]
    [string]$ArchiveRoot,
    [Parameter(Mandatory = $true)]
    [string]$PackageOutputRoot,
    [Parameter(Mandatory = $true)]
    [string]$LogRoot,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9]{64}$')]
    [string]$ExpectedClientSHA256
)

$ErrorActionPreference = 'Stop'
$expectedClientSha256 = $ExpectedClientSHA256.ToUpperInvariant()

function Get-FullPath([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    if ($full.Length -gt 3) { $full = $full.TrimEnd('\') }
    return $full
}

function Test-IsUnder([string]$Child, [string]$Parent) {
    return $Child.Equals($Parent, [System.StringComparison]::OrdinalIgnoreCase) -or
        $Child.StartsWith($Parent + '\', [System.StringComparison]::OrdinalIgnoreCase)
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runName = "BUILD-RECOVERY-PACKAGE-v-1.0.0-$stamp"
$runDir = Join-Path $LogRoot $runName
$runLog = Join-Path $runDir 'RUN.log'
$resultReport = Join-Path $runDir 'RESULT.tsv'
$transcriptStarted = $false
$packageRoot = $null

try {
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
    Start-Transcript -LiteralPath $runLog -Force | Out-Null
    $transcriptStarted = $true

    $recoveryFull = Get-FullPath $RecoveryRoot
    $archiveFull = Get-FullPath $ArchiveRoot
    $outputFull = Get-FullPath $PackageOutputRoot

    Write-Host 'BUILD RECOVERY PACKAGE v1.0.0'
    Write-Host "RECOVERY SOURCE (READ-ONLY): $recoveryFull"
    Write-Host "PACKAGE OUTPUT: $outputFull"
    Write-Host "LOG: $runLog"
    Write-Host 'SAFETY: no active-install writes; no source deletes; no /MIR'
    Write-Host 'CARD ART: excluded from recovery source and package'

    if (-not (Test-Path -LiteralPath $recoveryFull -PathType Container)) { throw "RecoveryRoot no existe: $recoveryFull" }
    if (-not (Test-Path -LiteralPath $archiveFull -PathType Container)) { throw "ArchiveRoot no existe: $archiveFull" }
    if (-not (Test-IsUnder $recoveryFull $archiveFull)) { throw 'Safety stop: RecoveryRoot fuera de ArchiveRoot' }
    if ($recoveryFull -match '(?i)\\(PRIVADO-BLINDADO-XMAGE|RC1\.1-COMPLETA-PORTABLE)(\\|$)') { throw 'Safety stop: no se empaqueta una base blindada' }

    $latestVerification = Get-ChildItem -LiteralPath $LogRoot -Directory -Force -ErrorAction Stop |
        Where-Object { $_.Name -like 'VERIFY-RECOVERY-CLONE-*' } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latestVerification) { throw 'No se encontró una validación RECOVERY_CLONE_VERIFIED' }
    $verificationResult = Join-Path $latestVerification.FullName 'RESULT.tsv'
    if (-not (Test-Path -LiteralPath $verificationResult -PathType Leaf)) { throw "Falta resultado de validación: $verificationResult" }
    $verification = @(Import-Csv -LiteralPath $verificationResult -Delimiter ([char]9) | Where-Object { $_.Status -eq 'RECOVERY_CLONE_VERIFIED' })
    if ($verification.Count -ne 1) { throw "La última validación no es RECOVERY_CLONE_VERIFIED: $verificationResult" }
    Write-Host "VERIFICATION ACCEPTED: $verificationResult"

    $manifestPath = Join-Path $recoveryFull 'RECOVERY-MANIFEST.tsv'
    $clientJarPath = Join-Path $recoveryFull 'client\lib\mage-client-1.4.61.jar'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Falta manifiesto: $manifestPath" }
    if (-not (Test-Path -LiteralPath $clientJarPath -PathType Leaf)) { throw "Falta client JAR: $clientJarPath" }
    $clientHash = (Get-FileHash -LiteralPath $clientJarPath -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($clientHash -ne $expectedClientSha256) { throw "Client JAR no coincide: $clientHash" }

    $forbiddenFiles = @(Get-ChildItem -LiteralPath $recoveryFull -Recurse -File -Force |
        Where-Object { $_.Name -match '(?i)\.log(\..*)?$' })
    if ($forbiddenFiles.Count -ne 0) { throw "La fuente contiene logs: $($forbiddenFiles.Count)" }
    $cardArtDirs = @(Get-ChildItem -LiteralPath $recoveryFull -Recurse -Directory -Force |
        Where-Object { $_.Name -in @('images','avatars','card-images','card_images','card-art','card_art') -and $_.FullName -match '(?i)\\client\\' })
    $cardArtFiles = @()
    foreach ($dir in $cardArtDirs) { $cardArtFiles += @(Get-ChildItem -LiteralPath $dir.FullName -Recurse -File -Force -ErrorAction SilentlyContinue) }
    if ($cardArtFiles.Count -ne 0) { throw "La fuente contiene arte de cartas: $($cardArtFiles.Count)" }

    New-Item -ItemType Directory -Path $outputFull -Force | Out-Null
    $packageRoot = Join-Path $outputFull "RECOVERY-PACKAGE-CURRENT-v-1.0.0-$stamp"
    if (Test-Path -LiteralPath $packageRoot) { throw "El destino ya existe; no se sobrescribe: $packageRoot" }
    $packageContent = Join-Path $packageRoot 'PACKAGE-CONTENT'
    $payloadRoot = Join-Path $packageContent 'PAYLOAD'
    $zipPath = Join-Path $packageRoot 'XMage-RECOVERY-CLONE-v-1.0.0.zip'
    New-Item -ItemType Directory -Path $payloadRoot -Force | Out-Null

    $copyArgs = @($recoveryFull, $payloadRoot, '/E', '/COPY:DAT', '/DCOPY:DAT', '/XJ', '/R:1', '/W:1', '/NP', '/NFL', '/NDL')
    Write-Host 'COPY: recovery source to package payload; no /MIR'
    $copyOutput = & robocopy @copyArgs 2>&1
    $copyOutput | ForEach-Object { Write-Host $_ }
    $copyCode = $LASTEXITCODE
    Write-Host "ROBOCOPY EXIT: $copyCode"
    if ($copyCode -ge 8) { throw "Robocopy package copy failed: $copyCode" }
    $payloadFiles = @(Get-ChildItem -LiteralPath $payloadRoot -Recurse -File -Force)
    $payloadBytes = ($payloadFiles | Measure-Object -Property Length -Sum).Sum
    Write-Host "PAYLOAD FILES: $($payloadFiles.Count)"
    Write-Host "PAYLOAD BYTES: $payloadBytes"

    $installerPs1 = @'
[CmdletBinding()]
param([string]$TargetRoot)

$ErrorActionPreference = 'Stop'
$expectedClientSha256 = '__EXPECTED_CLIENT_SHA256__'
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$payloadRoot = Join-Path $packageRoot 'PAYLOAD'
$logRoot = Join-Path $packageRoot 'INSTALL-LOGS'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runDir = Join-Path $logRoot "INSTALL-$stamp"
$runLog = Join-Path $runDir 'RUN.log'
$transcriptStarted = $false

try {
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
    Start-Transcript -LiteralPath $runLog -Force | Out-Null
    $transcriptStarted = $true
    Write-Host 'INSTALL RECOVERY CLONE v1.0.0'
    Write-Host "PAYLOAD: $payloadRoot"
    Write-Host 'SAFETY: existing non-empty target is never overwritten; no /MIR; no deletes'
    Write-Host 'CARD ART: excluded; restore separately from official image source or backup'

    if (-not (Test-Path -LiteralPath $payloadRoot -PathType Container)) { throw "PAYLOAD no existe: $payloadRoot" }
    if ([string]::IsNullOrWhiteSpace($TargetRoot)) { $TargetRoot = Read-Host 'Ruta destino nueva para XMage' }
    if ([string]::IsNullOrWhiteSpace($TargetRoot)) { throw 'No se indicó destino' }
    $targetFull = [System.IO.Path]::GetFullPath($TargetRoot)
    if ($targetFull.Equals($packageRoot, [System.StringComparison]::OrdinalIgnoreCase) -or $targetFull.StartsWith($packageRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Safety stop: destino dentro del paquete' }
    if (Test-Path -LiteralPath $targetFull) {
        $existing = @(Get-ChildItem -LiteralPath $targetFull -Force -ErrorAction Stop)
        if ($existing.Count -ne 0) { throw "Destino existente no vacío; no se sobrescribe: $targetFull" }
    } else {
        New-Item -ItemType Directory -Path $targetFull -Force | Out-Null
    }

    $copyArgs = @($payloadRoot, $targetFull, '/E', '/COPY:DAT', '/DCOPY:DAT', '/XJ', '/R:1', '/W:1', '/NP')
    $copyOutput = & robocopy @copyArgs 2>&1
    $copyOutput | ForEach-Object { Write-Host $_ }
    $copyCode = $LASTEXITCODE
    if ($copyCode -ge 8) { throw "Robocopy installation failed: $copyCode" }

    $clientJar = Join-Path $targetFull 'client\lib\mage-client-1.4.61.jar'
    if (-not (Test-Path -LiteralPath $clientJar -PathType Leaf)) { throw 'Instalación incompleta: falta client JAR' }
    $clientHash = (Get-FileHash -LiteralPath $clientJar -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($clientHash -ne $expectedClientSha256) { throw "Client JAR instalado no coincide: $clientHash" }
    Write-Host "RESULT: INSTALL_OK"
    Write-Host "TARGET: $targetFull"
    Write-Host "CLIENT JAR SHA256: $clientHash"
    Write-Host "RUN LOG: $runLog"
}
catch {
    Write-Host "ABORTED: $($_.Exception.Message)"
    exit 1
}
finally {
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
}
'@
    $installerPs1 = $installerPs1.Replace('__EXPECTED_CLIENT_SHA256__', $expectedClientSha256)

    $installerCmd = @'
@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL-RECOVERY-CLONE.ps1"
set "EXITCODE=%ERRORLEVEL%"
echo.
echo Instalacion finalizada con codigo %EXITCODE%.
pause
exit /b %EXITCODE%
'@

    $packageReadme = @'
XMAGE RECOVERY CLONE v1.0.0
========================================

Contenido: runtime XMage 1.4.61 de la instalación estable validada.
Incluye: cliente, servidor, Java incluido, launcher, configuración y mazos presentes en la copia.
Excluye: imágenes de cartas/avatares, logs e historiales volátiles.

INSTALACIÓN
1. Extrae este ZIP completo.
2. Ejecuta INSTALL-RECOVERY-CLONE.cmd.
3. Indica una carpeta destino nueva para XMage.
4. No se sobrescribe ninguna carpeta existente que contenga archivos.

La instalación conserva la pareja cliente/servidor 1.4.61 y la configuración incluida en el payload.
La escala UI 1.5 y la memoria de cliente de 4 GB deben mantenerse en el launcher/configuración.
Las imágenes se restauran aparte mediante la copia o el enlace oficial; no forman parte de este ZIP.

Cada instalación genera INSTALL-LOGS\<timestamp>\RUN.log.
'@

    Set-Content -LiteralPath (Join-Path $packageContent 'INSTALL-RECOVERY-CLONE.ps1') -Value $installerPs1 -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $packageContent 'INSTALL-RECOVERY-CLONE.cmd') -Value $installerCmd -Encoding ASCII
    Set-Content -LiteralPath (Join-Path $packageContent 'README-INSTALL.txt') -Value $packageReadme -Encoding UTF8

    $compressor = Get-Command 7z.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $compressor) { $compressor = Get-Command 7zz.exe -ErrorAction SilentlyContinue | Select-Object -First 1 }
    if ($compressor) {
        Push-Location $packageContent
        try {
            Write-Host "ARCHIVE: $($compressor.Source)"
            & $compressor.Source a -tzip -mx=1 -y $zipPath '*' 2>&1 | ForEach-Object { Write-Host $_ }
            $archiveCode = $LASTEXITCODE
        } finally { Pop-Location }
        if ($archiveCode -ge 2) { throw "ZIP creation failed: $archiveCode" }
    } else {
        if ([int64]$payloadBytes -gt 1900000000) { throw 'No se encontró 7-Zip y el payload supera el límite seguro de Compress-Archive; instala 7-Zip y repite sin tocar la copia' }
        Write-Host 'ARCHIVE: Compress-Archive fallback'
        Compress-Archive -Path (Join-Path $packageContent '*') -DestinationPath $zipPath -CompressionLevel Fastest -Force
        $archiveCode = 0
    }

    $zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToUpperInvariant()
    $zipSize = (Get-Item -LiteralPath $zipPath -Force).Length
    $hashText = @(
        'XMage Recovery Clone v1.0.0'
        "ZIP: $zipPath"
        "SHA256: $zipHash"
        "BYTES: $zipSize"
        "CLIENT JAR SHA256: $clientHash"
        'CARD ART: excluded'
        'NO MIR: true'
        'ACTIVE INSTALL MODIFIED: false'
    )
    $hashText | Set-Content -LiteralPath (Join-Path $packageRoot 'XMage-RECOVERY-CLONE-v-1.0.0.SHA256.txt') -Encoding UTF8

    [PSCustomObject][ordered]@{
        Status = 'RECOVERY_PACKAGE_BUILT'
        PackageRoot = $packageRoot
        Zip = $zipPath
        ZipSHA256 = $zipHash
        ZipBytes = $zipSize
        ClientJarSHA256 = $clientHash
        VerificationResult = $verificationResult
        CardArtExcluded = $true
        ActiveInstallationModified = $false
        RecoverySourceModified = $false
        DeletesPerformed = $false
        MirUsed = $false
    } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

    Write-Host 'RESULT: RECOVERY_PACKAGE_BUILT'
    Write-Host "ZIP: $zipPath"
    Write-Host "ZIP SHA256: $zipHash"
    Write-Host "SHA256 FILE: $(Join-Path $packageRoot 'XMage-RECOVERY-CLONE-v-1.0.0.SHA256.txt')"
    Write-Host "RESULT REPORT: $resultReport"
}
catch {
    Write-Host "ABORTED: $($_.Exception.Message)"
    try {
        [PSCustomObject][ordered]@{
            Status = 'ABORTED'
            Error = $_.Exception.Message
            PackageRoot = $packageRoot
            ActiveInstallationModified = $false
            RecoverySourceModified = $false
            DeletesPerformed = $false
            MirUsed = $false
        } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8
    } catch { Write-Host "REPORT ERROR: $($_.Exception.Message)" }
    exit 1
}
finally {
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
}
