[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RecoveryRoot,
    [Parameter(Mandatory = $true)]
    [string]$RestoredRoot,
    [Parameter(Mandatory = $true)]
    [string]$ArchiveRoot,
    [Parameter(Mandatory = $true)]
    [string]$LogRoot,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9]{64}$')]
    [string]$ExpectedClientSHA256
)

$ErrorActionPreference = 'Stop'
$expectedClientHash = $ExpectedClientSHA256.ToUpperInvariant()

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
$runName = "COMPARE-RECOVERY-RESTORE-v-1.0.0-$stamp"
$runDir = Join-Path $LogRoot $runName
$runLog = Join-Path $runDir 'RUN.log'
$resultReport = Join-Path $runDir 'RESULT.tsv'
$transcriptStarted = $false

try {
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
    Start-Transcript -LiteralPath $runLog -Force | Out-Null
    $transcriptStarted = $true

    $recoveryFull = Get-FullPath $RecoveryRoot
    $restoredFull = Get-FullPath $RestoredRoot
    $archiveFull = Get-FullPath $ArchiveRoot
    $manifestPath = Join-Path $recoveryFull 'RECOVERY-MANIFEST.tsv'

    Write-Host 'COMPARE RECOVERY SOURCE VS RESTORED INSTALL v1.0.0'
    Write-Host "RECOVERY SOURCE (READ-ONLY): $recoveryFull"
    Write-Host "RESTORED INSTALL (READ-ONLY): $restoredFull"
    Write-Host "MANIFEST: $manifestPath"
    Write-Host "LOG: $runLog"
    Write-Host 'SAFETY: no writes; no deletes; no /MIR; active installation is not involved'

    if (-not (Test-Path -LiteralPath $recoveryFull -PathType Container)) { throw "RecoveryRoot no existe: $recoveryFull" }
    if (-not (Test-Path -LiteralPath $restoredFull -PathType Container)) { throw "RestoredRoot no existe: $restoredFull" }
    if (-not (Test-IsUnder $recoveryFull $archiveFull)) { throw 'Safety stop: recovery fuera de ArchiveRoot' }
    if (-not (Test-IsUnder $restoredFull $archiveFull)) { throw 'Safety stop: restored fuera de ArchiveRoot' }
    if ($recoveryFull.Equals($restoredFull, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Safety stop: source y restored coinciden' }
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Falta manifiesto: $manifestPath" }

    $manifestLines = @(Get-Content -LiteralPath $manifestPath -ErrorAction Stop)
    $dataLines = @($manifestLines | Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and $_ -notmatch '^\s*#' })
    if ($dataLines.Count -eq 0) { throw 'Manifiesto vacío' }
    $delimiter = if ($dataLines[0] -match "`t") { [char]9 } elseif ($dataLines[0] -match ';') { ';' } elseif ($dataLines[0] -match ',') { ',' } else { throw 'Separador de manifiesto no reconocido' }
    $firstFields = @($dataLines[0].Split([char]$delimiter))
    $rows = @()
    if ($firstFields.Count -ge 4 -and $firstFields[1].Trim().Trim('"') -match '^\d+$' -and $firstFields[3].Trim().Trim('"') -match '^[A-Fa-f0-9]{64}$') {
        Write-Host 'MANIFEST FORMAT: headerless path/length/timestamp/SHA256'
        foreach ($line in $dataLines) {
            $fields = @($line.Split([char]$delimiter))
            if ($fields.Count -lt 4) { throw "Registro incompleto: $line" }
            $rows += [PSCustomObject][ordered]@{
                RelativePath = $fields[0].Trim().Trim('"')
                Length = $fields[1].Trim().Trim('"')
                SHA256 = $fields[3].Trim().Trim('"').ToUpperInvariant()
            }
        }
    } else {
        $rows = @(($dataLines | ConvertFrom-Csv -Delimiter $delimiter))
        if ($rows.Count -eq 0) { throw 'Manifiesto vacío' }
    }

    $seen = @{}
    $verified = 0
    foreach ($row in $rows) {
        $relative = [string]$row.RelativePath
        if ([string]::IsNullOrWhiteSpace($relative)) { throw 'Registro sin ruta' }
        $relative = $relative.Replace('/','\').Trim().Trim('"')
        if ([System.IO.Path]::IsPathRooted($relative)) { throw "Ruta absoluta no permitida: $relative" }
        if ($relative -match '(^|[\\/])\.\.([\\/]|$)') { throw "Ruta insegura: $relative" }
        $key = $relative.Replace('\','/').ToLowerInvariant()
        if ($seen.ContainsKey($key)) { throw "Ruta duplicada: $relative" }
        $seen[$key] = $true
        $sourceFile = Get-Item -LiteralPath (Join-Path $recoveryFull $relative) -Force
        $restoredFile = Get-Item -LiteralPath (Join-Path $restoredFull $relative) -Force
        if ($null -eq $sourceFile -or $null -eq $restoredFile) { throw "Falta archivo: $relative" }
        if ($sourceFile.Length -ne $restoredFile.Length) { throw "Tamaño distinto: $relative" }
        $sourceHash = (Get-FileHash -LiteralPath $sourceFile.FullName -Algorithm SHA256).Hash.ToUpperInvariant()
        $restoredHash = (Get-FileHash -LiteralPath $restoredFile.FullName -Algorithm SHA256).Hash.ToUpperInvariant()
        $expectedHash = [string]$row.SHA256
        if ($sourceHash -ne $expectedHash) { throw "Manifiesto no coincide con source: $relative" }
        if ($restoredHash -ne $expectedHash) { throw "Restored no coincide: $relative" }
        $verified++
    }

    $restoredExtra = @(Get-ChildItem -LiteralPath $restoredFull -Recurse -File -Force | Where-Object {
        $relative = $_.FullName.Substring($restoredFull.Length).TrimStart('\').Replace('\','/').ToLowerInvariant()
        -not $seen.ContainsKey($relative)
    })
    $allowedExtra = @($restoredExtra | Where-Object { $_.Name -eq 'RECOVERY-MANIFEST.tsv' })
    $unexpectedExtra = @($restoredExtra | Where-Object { $_.Name -ne 'RECOVERY-MANIFEST.tsv' })
    if ($unexpectedExtra.Count -ne 0) { throw "Archivos extra en restored: $($unexpectedExtra.Count)" }

    $clientJar = Join-Path $restoredFull 'client\lib\mage-client-1.4.61.jar'
    $restoredClientHash = (Get-FileHash -LiteralPath $clientJar -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($restoredClientHash -ne $expectedClientHash) { throw "Client JAR restored no coincide: $restoredClientHash" }

    [PSCustomObject][ordered]@{
        Status = 'RECOVERY_RESTORE_EXACT_MATCH'
        RecoveryRoot = $recoveryFull
        RestoredRoot = $restoredFull
        ManifestRows = $rows.Count
        VerifiedFiles = $verified
        RestoredExtraMetadata = $allowedExtra.Count
        UnexpectedExtraFiles = $unexpectedExtra.Count
        ClientJarSHA256 = $restoredClientHash
        ActiveInstallationModified = $false
        RecoverySourceModified = $false
        RestoredRootModified = $false
        DeletesPerformed = $false
        MirUsed = $false
    } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

    Write-Host "MANIFEST ROWS: $($rows.Count)"
    Write-Host "VERIFIED FILES: $verified"
    Write-Host "UNEXPECTED EXTRA FILES: $($unexpectedExtra.Count)"
    Write-Host 'RESULT: RECOVERY_RESTORE_EXACT_MATCH'
    Write-Host "RESULT REPORT: $resultReport"
}
catch {
    Write-Host "ABORTED: $($_.Exception.Message)"
    try {
        [PSCustomObject][ordered]@{
            Status = 'ABORTED'
            Error = $_.Exception.Message
            RecoveryRoot = $RecoveryRoot
            RestoredRoot = $RestoredRoot
            ActiveInstallationModified = $false
            RecoverySourceModified = $false
            RestoredRootModified = $false
            DeletesPerformed = $false
            MirUsed = $false
        } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8
    } catch { Write-Host "REPORT ERROR: $($_.Exception.Message)" }
    exit 1
}
finally {
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
}
