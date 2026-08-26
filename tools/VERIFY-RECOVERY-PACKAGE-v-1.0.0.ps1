[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ZipPath,
    [Parameter(Mandatory = $true)]
    [string]$ArchiveRoot,
    [Parameter(Mandatory = $true)]
    [string]$LogRoot,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9]{64}$')]
    [string]$ExpectedZipSHA256,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9]{64}$')]
    [string]$ExpectedClientSHA256,
    [switch]$SmokeInstall
)

$ErrorActionPreference = 'Stop'
$expectedZipHash = $ExpectedZipSHA256.ToUpperInvariant()
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

function Get-EntryHash([System.IO.Compression.ZipArchiveEntry]$Entry) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $stream = $Entry.Open()
        try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToUpperInvariant() }
        finally { $stream.Dispose() }
    } finally { $sha.Dispose() }
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runName = "VERIFY-RECOVERY-PACKAGE-v-1.0.0-$stamp"
$runDir = Join-Path $LogRoot $runName
$runLog = Join-Path $runDir 'RUN.log'
$resultReport = Join-Path $runDir 'RESULT.tsv'
$transcriptStarted = $false
$archive = $null
$smokeRoot = $null
$resultStatus = 'RECOVERY_PACKAGE_VERIFIED'

try {
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
    Start-Transcript -LiteralPath $runLog -Force | Out-Null
    $transcriptStarted = $true

    $zipFull = Get-FullPath $ZipPath
    $archiveFull = Get-FullPath $ArchiveRoot
    Write-Host 'VERIFY RECOVERY PACKAGE v1.0.0'
    Write-Host "ZIP (READ-ONLY): $zipFull"
    Write-Host "ARCHIVE ROOT: $archiveFull"
    Write-Host "LOG: $runLog"
    Write-Host 'SAFETY: ZIP and source are read-only; smoke destination is new; no /MIR; no deletes'
    Write-Host 'CARD ART: forbidden in ZIP'

    if (-not (Test-Path -LiteralPath $zipFull -PathType Leaf)) { throw "ZIP no existe: $zipFull" }
    if (-not (Test-IsUnder $zipFull $archiveFull)) { throw 'Safety stop: ZIP fuera de ArchiveRoot' }

    $zipHash = (Get-FileHash -LiteralPath $zipFull -Algorithm SHA256).Hash.ToUpperInvariant()
    Write-Host "ZIP SHA256: $zipHash"
    if ($zipHash -ne $expectedZipHash) { throw "ZIP SHA256 distinto: $zipHash" }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($zipFull)
    $entries = @($archive.Entries | Where-Object { -not [string]::IsNullOrWhiteSpace($_.Name) })
    if ($entries.Count -eq 0) { throw 'ZIP vacío' }

    $required = @(
        'INSTALL-RECOVERY-CLONE.cmd',
        'INSTALL-RECOVERY-CLONE.ps1',
        'README-INSTALL.txt',
        'PAYLOAD/XMageLauncher-0.3.8.jar',
        'PAYLOAD/client/lib/mage-client-1.4.61.jar',
        'PAYLOAD/server/lib/mage-server-1.4.61.jar'
    )
    foreach ($name in $required) {
        if (-not ($entries | Where-Object { $_.FullName.Replace('\','/') -eq $name })) { throw "Falta entrada esencial: $name" }
    }

    $badEntries = @($entries | Where-Object {
        $normalized = $_.FullName.Replace('\','/').ToLowerInvariant()
        $_.Name -match '(?i)\.log(\..*)?$' -or
        $normalized -match '/(plugins/images|avatars|card-images|card_images|card-art|card_art)(/|$)' -or
        $normalized -match '(^|/)install-logs(/|$)'
    })
    if ($badEntries.Count -ne 0) { throw "Entradas prohibidas en ZIP: $($badEntries.Count)" }

    $clientEntry = $entries | Where-Object { $_.FullName.Replace('\','/') -eq 'PAYLOAD/client/lib/mage-client-1.4.61.jar' } | Select-Object -First 1
    $nestedClientHash = Get-EntryHash $clientEntry
    Write-Host "PACKAGED CLIENT JAR SHA256: $nestedClientHash"
    if ($nestedClientHash -ne $expectedClientHash) { throw "Client JAR dentro del ZIP no coincide: $nestedClientHash" }

    $totalUncompressed = ($entries | Measure-Object -Property Length -Sum).Sum
    Write-Host "ZIP FILE ENTRIES: $($entries.Count)"
    Write-Host "ZIP UNCOMPRESSED BYTES: $totalUncompressed"
    Write-Host 'ARCHIVE CONTENT: valid; no card art; no logs'

    if ($SmokeInstall) {
        $archive.Dispose()
        $archive = $null
        $smokeRoot = Join-Path $archiveFull "RECOVERY-PACKAGE-SMOKE-v-1.0.0-$stamp"
        if (Test-Path -LiteralPath $smokeRoot) { throw "Smoke destination already exists; no overwrite: $smokeRoot" }
        $extractRoot = Join-Path $smokeRoot 'EXTRACTED'
        $smokeInstallRoot = Join-Path $smokeRoot 'RESTORED-INSTALL'
        New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null
        Write-Host "SMOKE EXTRACT (NEW DESTINATION): $extractRoot"
        Expand-Archive -LiteralPath $zipFull -DestinationPath $extractRoot
        $smokeInstaller = Join-Path $extractRoot 'INSTALL-RECOVERY-CLONE.ps1'
        if (-not (Test-Path -LiteralPath $smokeInstaller -PathType Leaf)) { throw 'Smoke: falta INSTALL-RECOVERY-CLONE.ps1' }
        Write-Host "SMOKE INSTALL (NEW DESTINATION): $smokeInstallRoot"
        $smokeOutput = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $smokeInstaller -TargetRoot $smokeInstallRoot 2>&1
        $smokeOutput | ForEach-Object { Write-Host $_ }
        $smokeCode = $LASTEXITCODE
        if ($smokeCode -ne 0) { throw "Smoke installer failed: $smokeCode" }
        $smokeClientJar = Join-Path $smokeInstallRoot 'client\lib\mage-client-1.4.61.jar'
        if (-not (Test-Path -LiteralPath $smokeClientJar -PathType Leaf)) { throw 'Smoke: falta client JAR instalado' }
        $smokeClientHash = (Get-FileHash -LiteralPath $smokeClientJar -Algorithm SHA256).Hash.ToUpperInvariant()
        if ($smokeClientHash -ne $expectedClientHash) { throw "Smoke client JAR no coincide: $smokeClientHash" }
        $resultStatus = 'RECOVERY_PACKAGE_SMOKE_OK'
        Write-Host "SMOKE CLIENT JAR SHA256: $smokeClientHash"
        Write-Host "SMOKE ROOT: $smokeRoot"
    }

    [PSCustomObject][ordered]@{
        Status = $resultStatus
        Zip = $zipFull
        ZipSHA256 = $zipHash
        ZipEntries = $entries.Count
        ZipUncompressedBytes = $totalUncompressed
        ClientJarSHA256 = $nestedClientHash
        ForbiddenEntries = $badEntries.Count
        SmokeInstall = [bool]$SmokeInstall
        SmokeRoot = $smokeRoot
        ArchiveSourceModified = $false
        ActiveInstallationModified = $false
        DeletesPerformed = $false
        MirUsed = $false
    } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

    Write-Host "RESULT: $resultStatus"
    Write-Host "RESULT REPORT: $resultReport"
}
catch {
    Write-Host "ABORTED: $($_.Exception.Message)"
    try {
        [PSCustomObject][ordered]@{
            Status = 'ABORTED'
            Error = $_.Exception.Message
            Zip = $ZipPath
            ArchiveSourceModified = $false
            ActiveInstallationModified = $false
            DeletesPerformed = $false
            MirUsed = $false
        } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8
    } catch { Write-Host "REPORT ERROR: $($_.Exception.Message)" }
    exit 1
}
finally {
    if ($null -ne $archive) { $archive.Dispose() }
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
}
