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
$runName = "VERIFY-RECOVERY-CLONE-v-1.0.0-$stamp"
$runDir = Join-Path $LogRoot $runName
$runLog = Join-Path $runDir 'RUN.log'
$resultReport = Join-Path $runDir 'RESULT.tsv'
$transcriptStarted = $false

try {
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
    Start-Transcript -LiteralPath $runLog -Force | Out-Null
    $transcriptStarted = $true

    $archiveFull = Get-FullPath $ArchiveRoot
    $installFull = Get-FullPath $InstallRoot
    $recoveryFull = Get-FullPath $RecoveryRoot
    $manifestPath = Join-Path $recoveryFull 'RECOVERY-MANIFEST.tsv'

    Write-Host 'VERIFY RECOVERY CLONE v1.0.0'
    Write-Host "ACTIVE INSTALL (READ-ONLY): $installFull"
    Write-Host "RECOVERY COPY (READ-ONLY): $recoveryFull"
    Write-Host "MANIFEST: $manifestPath"
    Write-Host "LOG: $runLog"
    Write-Host 'SAFETY: no writes to install or recovery copy; no deletes; no /MIR'
    Write-Host 'CARD ART: must remain excluded'

    if (-not (Test-Path -LiteralPath $installFull -PathType Container)) { throw "No existe la instalación activa: $installFull" }
    if (-not (Test-Path -LiteralPath $recoveryFull -PathType Container)) { throw "No existe la copia: $recoveryFull" }
    if (-not (Test-IsUnder $recoveryFull $archiveFull)) { throw 'Safety stop: recovery copy fuera de ArchiveRoot' }
    if ($recoveryFull.Equals($installFull, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Safety stop: recovery coincide con la instalación activa' }
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Falta RECOVERY-MANIFEST.tsv: $manifestPath" }

    foreach ($relative in @(
        'XMageLauncher-0.3.8.jar',
        'client\lib\mage-client-1.4.61.jar',
        'server\lib\mage-server-1.4.61.jar',
        'client\config',
        'client\sample-decks',
        'java\jre17'
    )) {
        if (-not (Test-Path -LiteralPath (Join-Path $recoveryFull $relative))) {
            throw "Falta elemento esencial: $relative"
        }
    }

    $clientJar = Get-Item -LiteralPath (Join-Path $recoveryFull 'client\lib\mage-client-1.4.61.jar') -Force
    $clientHash = (Get-FileHash -LiteralPath $clientJar.FullName -Algorithm SHA256).Hash.ToUpperInvariant()
    Write-Host "CLIENT JAR SHA256: $clientHash"
    if ($clientHash -ne $expectedClientSha256) { throw "Client JAR no coincide: $clientHash" }

    $forbiddenFiles = @(Get-ChildItem -LiteralPath $recoveryFull -Recurse -File -Force |
        Where-Object { $_.Name -match '(?i)\.log(\..*)?$' })
    if ($forbiddenFiles.Count -ne 0) { throw "Hay logs dentro de la copia: $($forbiddenFiles.Count)" }

    $cardArtDirs = @(Get-ChildItem -LiteralPath $recoveryFull -Recurse -Directory -Force |
        Where-Object { $_.Name -in @('images','avatars','card-images','card_images','card-art','card_art') -and $_.FullName -match '(?i)\\client\\' })
    $cardArtFiles = @()
    foreach ($dir in $cardArtDirs) {
        $cardArtFiles += @(Get-ChildItem -LiteralPath $dir.FullName -Recurse -File -Force -ErrorAction SilentlyContinue)
    }
    if ($cardArtFiles.Count -ne 0) { throw "Hay imágenes/arte de cartas: $($cardArtFiles.Count)" }

    $rows = @(Import-Csv -LiteralPath $manifestPath -Delimiter ([char]9))
    if ($rows.Count -eq 0) { throw 'El manifiesto está vacío' }
    if (-not ($rows[0].PSObject.Properties.Name -contains 'RelativePath') -or
        -not ($rows[0].PSObject.Properties.Name -contains 'Length') -or
        -not ($rows[0].PSObject.Properties.Name -contains 'SHA256')) {
        throw 'Formato de manifiesto inválido'
    }

    $seen = @{}
    $verified = 0
    foreach ($row in $rows) {
        $relative = [string]$row.RelativePath
        if ([string]::IsNullOrWhiteSpace($relative) -or [System.IO.Path]::IsPathRooted($relative) -or $relative -match '(^|[\\/])\.\.([\\/]|$)') {
            throw "Ruta insegura en manifiesto: $relative"
        }
        $key = $relative.Replace('\','/').ToLowerInvariant()
        if ($seen.ContainsKey($key)) { throw "Ruta duplicada en manifiesto: $relative" }
        $seen[$key] = $true
        $filePath = Join-Path $recoveryFull ($relative.Replace('/', '\'))
        if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) { throw "Falta archivo del manifiesto: $relative" }
        $file = Get-Item -LiteralPath $filePath -Force
        if ([int64]$row.Length -ne $file.Length) { throw "Tamaño distinto: $relative" }
        $actual = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToUpperInvariant()
        if ($actual -ne ([string]$row.SHA256).ToUpperInvariant()) { throw "SHA256 distinto: $relative" }
        $verified++
    }

    $extraFiles = @(Get-ChildItem -LiteralPath $recoveryFull -Recurse -File -Force | Where-Object {
        $relative = $_.FullName.Substring($recoveryFull.Length).TrimStart('\').Replace('\','/').ToLowerInvariant()
        -not $seen.ContainsKey($relative)
    })
    $allowedGenerated = @($extraFiles | Where-Object { $_.Name -in @('README-RECOVERY.txt') })
    $unexpectedExtra = @($extraFiles | Where-Object { $_.Name -notin @('README-RECOVERY.txt') })
    if ($unexpectedExtra.Count -ne 0) { throw "Archivos no incluidos en manifiesto: $($unexpectedExtra.Count)" }

    $allFiles = @(Get-ChildItem -LiteralPath $recoveryFull -Recurse -File -Force)
    $deckFiles = @($allFiles | Where-Object { $_.Extension -in @('.dck','.mwDeck') }).Count
    [PSCustomObject][ordered]@{
        Status = 'RECOVERY_CLONE_VERIFIED'
        RecoveryRoot = $recoveryFull
        ManifestRows = $rows.Count
        VerifiedFiles = $verified
        TotalFilesNow = $allFiles.Count
        ClientJarSHA256 = $clientHash
        DeckFiles = $deckFiles
        CardArtFiles = $cardArtFiles.Count
        LogFiles = $forbiddenFiles.Count
        AllowedMetadataExtras = $allowedGenerated.Count
        ActiveInstallationModified = $false
        RecoveryCopyModified = $false
        ProtectedBaseModified = $false
        DeletesPerformed = $false
        MirUsed = $false
    } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

    Write-Host "MANIFEST ROWS: $($rows.Count)"
    Write-Host "VERIFIED FILES: $verified"
    Write-Host "DECK FILES: $deckFiles"
    Write-Host 'RESULT: RECOVERY_CLONE_VERIFIED'
    Write-Host "RESULT REPORT: $resultReport"
}
catch {
    Write-Host "ABORTED: $($_.Exception.Message)"
    try {
        [PSCustomObject][ordered]@{
            Status = 'ABORTED'
            Error = $_.Exception.Message
            RecoveryRoot = $RecoveryRoot
            ActiveInstallationModified = $false
            RecoveryCopyModified = $false
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
