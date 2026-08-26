[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RecoveryRoot,
    [Parameter(Mandatory = $true)]
    [string]$ArchiveRoot,
    [Parameter(Mandatory = $true)]
    [string]$InstallRoot,
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
$runName = "FINALIZE-RECOVERY-CLONE-v-1.0.0-$stamp"
$runDir = Join-Path $LogRoot $runName
$runLog = Join-Path $runDir 'RUN.log'
$manifestPath = $null
$readmePath = $null
$privateReport = $null
$transcriptStarted = $false
$status = 'ABORTED'

try {
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
    Start-Transcript -LiteralPath $runLog -Force | Out-Null
    $transcriptStarted = $true

    $archiveFull = Get-FullPath $ArchiveRoot
    $installFull = Get-FullPath $InstallRoot

    if ([string]::IsNullOrWhiteSpace($RecoveryRoot)) {
        $candidate = Get-ChildItem -LiteralPath $archiveFull -Directory -Force -ErrorAction Stop |
            Where-Object { $_.Name -like 'RECOVERY-CLONE-CURRENT-v-1.0.0-*' } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if (-not $candidate) { throw "No se encontró una copia RECOVERY-CLONE-CURRENT-v-1.0.0-*" }
        $RecoveryRoot = $candidate.FullName
    }

    $recoveryFull = Get-FullPath $RecoveryRoot
    $manifestPath = Join-Path $recoveryFull 'RECOVERY-MANIFEST.tsv'
    $readmePath = Join-Path $recoveryFull 'README-RECOVERY.txt'
    $privateReport = Join-Path $runDir 'PRIVATE-CANDIDATES.tsv'
    $resultReport = Join-Path $runDir 'RESULT.tsv'

    Write-Host 'FINALIZE RECOVERY CLONE v1.0.0'
    Write-Host "ACTIVE INSTALL (READ-ONLY): $installFull"
    Write-Host "RECOVERY COPY: $recoveryFull"
    Write-Host "LOG: $runLog"
    Write-Host 'SAFETY: no active-install writes; no deletes; no /MIR'
    Write-Host 'CARD ART: excluded and not regenerated here'

    if (-not (Test-Path -LiteralPath $installFull -PathType Container)) { throw "No existe la instalación activa: $installFull" }
    if (-not (Test-Path -LiteralPath $recoveryFull -PathType Container)) { throw "No existe la copia: $recoveryFull" }
    if (-not (Test-IsUnder $recoveryFull $archiveFull)) { throw 'Safety stop: recovery copy fuera de ArchiveRoot' }
    if ($recoveryFull.Equals($installFull, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Safety stop: recovery copy coincide con la instalación activa' }
    if ($recoveryFull -match '(?i)\\(PRIVADO-BLINDADO-XMAGE|RC1\.1-COMPLETA-PORTABLE)(\\|$)') { throw 'Safety stop: no se usa una base blindada como recovery copy' }
    if (Test-Path -LiteralPath $manifestPath -PathType Leaf) { throw "No se sobrescribe el manifiesto existente: $manifestPath" }
    if (Test-Path -LiteralPath $readmePath -PathType Leaf) { throw "No se sobrescribe el README existente: $readmePath" }

    $required = @(
        'XMageLauncher-0.3.8.jar',
        'client\lib\mage-client-1.4.61.jar',
        'server\lib\mage-server-1.4.61.jar',
        'client\config',
        'client\sample-decks',
        'java\jre17'
    )
    foreach ($relative in $required) {
        if (-not (Test-Path -LiteralPath (Join-Path $recoveryFull $relative))) {
            throw "Falta elemento esencial: $relative"
        }
    }

    $clientJar = Get-Item -LiteralPath (Join-Path $recoveryFull 'client\lib\mage-client-1.4.61.jar') -Force
    $clientHash = (Get-FileHash -LiteralPath $clientJar.FullName -Algorithm SHA256).Hash.ToUpperInvariant()
    Write-Host "CLIENT JAR SHA256: $clientHash"
    if ($clientHash -ne $expectedClientSha256) { throw "El client JAR no coincide con el runtime activo: $clientHash" }

    $forbiddenFiles = @(Get-ChildItem -LiteralPath $recoveryFull -Recurse -File -Force |
        Where-Object { $_.Name -match '(?i)\.log(\..*)?$' })
    if ($forbiddenFiles.Count -ne 0) { throw "Hay logs dentro de la copia: $($forbiddenFiles.Count)" }

    $cardArtDirs = @(Get-ChildItem -LiteralPath $recoveryFull -Recurse -Directory -Force |
        Where-Object { $_.Name -in @('images','avatars','card-images','card_images','card-art','card_art') -and $_.FullName -match '(?i)\\client\\' })
    $cardArtFiles = @()
    foreach ($dir in $cardArtDirs) {
        $cardArtFiles += @(Get-ChildItem -LiteralPath $dir.FullName -Recurse -File -Force -ErrorAction SilentlyContinue)
    }
    if ($cardArtFiles.Count -ne 0) { throw "Hay imágenes/arte de cartas dentro de la copia: $($cardArtFiles.Count)" }

    $allFiles = @(Get-ChildItem -LiteralPath $recoveryFull -Recurse -File -Force)
    $manifestRows = foreach ($file in $allFiles) {
        $relative = $file.FullName.Substring($recoveryFull.Length).TrimStart('\').Replace('\','/')
        [PSCustomObject][ordered]@{
            RelativePath = $relative
            Length = $file.Length
            SHA256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToUpperInvariant()
        }
    }

    $manifestRows | Export-Csv -LiteralPath $manifestPath -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

    $privateCandidates = $allFiles | Where-Object {
        $_.Name -in @('installed.properties','preferences.xml','preferences.properties') -or
        $_.FullName -match '(?i)\\(profile|profiles|saved|gamelogs|gamesHistory|gamesHistoryJson)\\'
    } | ForEach-Object {
        [PSCustomObject][ordered]@{
            RelativePath = $_.FullName.Substring($recoveryFull.Length).TrimStart('\').Replace('\','/')
            Length = $_.Length
            Classification = 'PRIVATE_OR_MACHINE_SPECIFIC_REVIEW_REQUIRED'
        }
    }
    if ($privateCandidates) {
        $privateCandidates | Export-Csv -LiteralPath $privateReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8
    } else {
        'RelativePath`tLength`tClassification' | Set-Content -LiteralPath $privateReport -Encoding UTF8
    }

    @(
        'RECOVERY CLONE CURRENT v1.0.0'
        'Status: VALIDATED LOCALLY'
        'Base: active XMage 1.4.61 runtime snapshot'
        "Client JAR SHA256: $clientHash"
        "Files: $($allFiles.Count)"
        'Card-art/images: excluded'
        'Runtime logs and volatile history: excluded'
        'No /MIR used'
        'Active installation: never modified'
        'Protected bases: never modified'
        'This recovery copy is private until the candidate report is reviewed.'
        'Do not publish installed.properties or private candidates to public GitHub.'
    ) | Set-Content -LiteralPath $readmePath -Encoding UTF8

    [PSCustomObject][ordered]@{
        Status = 'RECOVERY_CLONE_VALIDATED'
        RecoveryRoot = $recoveryFull
        Files = $allFiles.Count
        Bytes = ($allFiles | Measure-Object -Property Length -Sum).Sum
        ClientJarSHA256 = $clientHash
        CardArtFiles = $cardArtFiles.Count
        LogFiles = $forbiddenFiles.Count
        Manifest = $manifestPath
        PrivateCandidates = $privateReport
        ActiveInstallationModified = $false
        ProtectedBaseModified = $false
        DeletesPerformed = $false
        MirUsed = $false
    } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

    $status = 'RECOVERY_CLONE_VALIDATED'
    Write-Host "RESULT: $status"
    Write-Host "MANIFEST: $manifestPath"
    Write-Host "PRIVATE REVIEW: $privateReport"
    Write-Host "RESULT REPORT: $resultReport"
}
catch {
    Write-Host "ABORTED: $($_.Exception.Message)"
    try {
        $resultReport = Join-Path $runDir 'RESULT.tsv'
        [PSCustomObject][ordered]@{
            Status = 'ABORTED'
            Error = $_.Exception.Message
            RecoveryRoot = $RecoveryRoot
            ActiveInstallationModified = $false
            ProtectedBaseModified = $false
            DeletesPerformed = $false
            MirUsed = $false
        } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8
    } catch { Write-Host "REPORT ERROR: $($_.Exception.Message)" }
    exit 1
}
finally {
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
}
