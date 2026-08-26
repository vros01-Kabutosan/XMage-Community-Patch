[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$StageRoot,
    [string]$InstallRoot = 'J:\mtg\xmage',
    [string]$LogRoot = 'J:\mtg\_LOGS'
)

$ErrorActionPreference = 'Stop'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runName = "COMPARE-STAGED-BUILD-VS-INSTALL-v-1.0.0-$stamp"
$runLogDir = Join-Path $LogRoot $runName
$runLog = Join-Path $runLogDir 'RUN.log'
$report = Join-Path $runLogDir 'JAR-CONTENT-COMPARISON.tsv'

New-Item -ItemType Directory -Path $runLogDir -Force | Out-Null
Start-Transcript -Path $runLog -Force

function Get-ZipEntryMap([string]$path) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($path)
    try {
        $map = @{}
        foreach ($entry in $archive.Entries) {
            if ([string]::IsNullOrEmpty($entry.Name) -or $entry.FullName -eq 'META-INF/MANIFEST.MF') { continue }
            $stream = $entry.Open()
            try {
                $sha = [System.Security.Cryptography.SHA256]::Create()
                try { $hash = ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '') }
                finally { $sha.Dispose() }
            } finally { $stream.Dispose() }
            $map[$entry.FullName] = "$($entry.Length):$hash"
        }
        return $map
    } finally { $archive.Dispose() }
}

function Compare-Jar([string]$label, [string]$built, [string]$active) {
    if (-not (Test-Path -LiteralPath $built -PathType Leaf)) {
        Write-Host "MISSING BUILT`t$label`t$built"
        "$label`tMISSING_BUILT`t$built`t$active" | Add-Content -LiteralPath $report
        return $false
    }
    if (-not (Test-Path -LiteralPath $active -PathType Leaf)) {
        Write-Host "MISSING ACTIVE`t$label`t$active"
        "$label`tMISSING_ACTIVE`t$built`t$active" | Add-Content -LiteralPath $report
        return $false
    }
    $builtMap = Get-ZipEntryMap $built
    $activeMap = Get-ZipEntryMap $active
    $allNames = @($builtMap.Keys + $activeMap.Keys | Sort-Object -Unique)
    $different = @($allNames | Where-Object { $builtMap[$_] -ne $activeMap[$_] })
    $status = if ($different.Count -eq 0) { 'MATCH' } else { 'MISMATCH' }
    Write-Host "$status`t$label`tentries=$($allNames.Count)`tdifferent=$($different.Count)"
    "$label`t$status`tentries=$($allNames.Count)`tdifferent=$($different.Count)`tbuilt=$built`tactive=$active" | Add-Content -LiteralPath $report
    foreach ($name in $different) {
        $builtValue = if ($builtMap.ContainsKey($name)) { $builtMap[$name] } else { '<missing>' }
        $activeValue = if ($activeMap.ContainsKey($name)) { $activeMap[$name] } else { '<missing>' }
        "DIFF`t$label`t$name`tbuilt=$builtValue`tactive=$activeValue" | Add-Content -LiteralPath $report
    }
    return ($different.Count -eq 0)
}

try {
    Write-Host "COMPARE STAGED BUILD VS ACTIVE INSTALL"
    Write-Host "Stage: $StageRoot"
    Write-Host "Install: $InstallRoot"
    Write-Host "READ-ONLY: active installation is never changed"
    if (-not (Test-Path -LiteralPath $StageRoot -PathType Container)) { throw "StageRoot not found" }
    if (-not (Test-Path -LiteralPath $InstallRoot -PathType Container)) { throw "InstallRoot not found" }
    "Label`tStatus`tDetails" | Set-Content -LiteralPath $report -Encoding UTF8

    $checks = @(
        @('Mage framework / server+client', 'Mage\target\mage-1.4.61.jar', 'server\lib\mage-1.4.61.jar'),
        @('Mage common', 'Mage.Common\target\mage-common-1.4.61.jar', 'server\lib\mage-common-1.4.61.jar'),
        @('Mage server', 'Mage.Server\target\mage-server-1.4.61.jar', 'server\lib\mage-server-1.4.61.jar'),
        @('Mage client', 'Mage.Client\target\mage-client-1.4.61.jar', 'client\lib\mage-client-1.4.61.jar'),
        @('Mage sets / server', 'Mage.Sets\target\mage-sets-1.4.61.jar', 'server\lib\mage-sets-1.4.61.jar'),
        @('Mage sets / client', 'Mage.Sets\target\mage-sets-1.4.61.jar', 'client\lib\mage-sets-1.4.61.jar')
    )
    $allPass = $true
    foreach ($check in $checks) {
        $allPass = (Compare-Jar $check[0] (Join-Path $StageRoot $check[1]) (Join-Path $InstallRoot $check[2])) -and $allPass
    }
    Write-Host "RESULT: $(if ($allPass) { 'PASS' } else { 'MISMATCHES FOUND' })"
    Write-Host "REPORT: $report"
} catch {
    Write-Host "ABORTED: $($_.Exception.Message)"
    throw
} finally {
    Stop-Transcript
}

Write-Host "RUN LOG: $runLog"
