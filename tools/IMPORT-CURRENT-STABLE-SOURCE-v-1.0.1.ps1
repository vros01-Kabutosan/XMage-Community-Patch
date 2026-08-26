[CmdletBinding()]
param(
    [string]$SourceRoot = 'J:\mtg\_ARCHIVO\00-FUENTE\rc1.1-complete-community',
    [string]$SuperiorSource = '',
    [string]$ArchiveRoot = 'J:\mtg\_ARCHIVO',
    [string]$LogRoot = 'J:\mtg\_LOGS'
)

$ErrorActionPreference = 'Stop'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runName = "IMPORT-CURRENT-STABLE-SOURCE-v-1.0.1-$stamp"
$stage = Join-Path $ArchiveRoot $runName
$runLogDir = Join-Path $LogRoot $runName
$runLog = Join-Path $runLogDir 'RUN.log'
$buildLog = Join-Path $runLogDir 'MAVEN-BUILD.log'
$manifest = Join-Path $runLogDir 'MANIFEST-SHA256.tsv'

New-Item -ItemType Directory -Path $runLogDir -Force | Out-Null
Start-Transcript -Path $runLog -Force

try {
    Write-Host "IMPORT CURRENT STABLE SOURCE v1.0.1"
    Write-Host "READ-ONLY INSTALLATION: J:\mtg\xmage is never touched"
    Write-Host "Source: $SourceRoot"
    Write-Host "Superior: $SuperiorSource"
    Write-Host "Stage: $stage"

    if (-not (Test-Path -LiteralPath $SourceRoot -PathType Container)) { throw "SourceRoot not found" }
    if (-not $SuperiorSource) {
        $modRoot = 'J:\mtg\_ARCHIVO\MODS\MOD-004-SUPERIOR-SPIDER-MAN-v-1.0.3'
        $candidates = Get-ChildItem -LiteralPath $modRoot -Recurse -File -Filter 'SuperiorSpiderMan.java' -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '\\target\\' } |
            Sort-Object LastWriteTime -Descending
        if (-not $candidates) { throw "SuperiorSpiderMan.java not found under MOD-004" }
        $SuperiorSource = $candidates[0].FullName
        Write-Host "SUPERIOR AUTODETECTED: $SuperiorSource"
    }
    if (-not (Test-Path -LiteralPath $SuperiorSource -PathType Leaf)) { throw "SuperiorSource not found: $SuperiorSource" }
    if (Test-Path -LiteralPath $stage) { throw "Refusing to overwrite existing stage: $stage" }

    New-Item -ItemType Directory -Path $stage -Force | Out-Null
    Write-Host "COPY: source without generated target/.git directories"
    & robocopy $SourceRoot $stage /E /XJ /R:1 /W:1 /COPY:DAT /DCOPY:DAT /XD target .git /LOG+:$runLog /NFL /NDL /NP
    $copyCode = $LASTEXITCODE
    if ($copyCode -ge 8) { throw "Robocopy failed with exit code $copyCode" }
    Write-Host "COPY OK: robocopy exit $copyCode"

    $superiorRelative = 'Mage.Sets\src\main\java\mage\cards\s\SuperiorSpiderMan.java'
    $superiorTarget = Join-Path $stage $superiorRelative
    New-Item -ItemType Directory -Path (Split-Path -Parent $superiorTarget) -Force | Out-Null
    Copy-Item -LiteralPath $SuperiorSource -Destination $superiorTarget -Force
    $superiorHash = (Get-FileHash -LiteralPath $superiorTarget -Algorithm SHA256).Hash
    Write-Host "SUPERIOR INTEGRATED: $superiorHash"

    $pom = Join-Path $stage 'pom.xml'
    if (-not (Test-Path -LiteralPath $pom -PathType Leaf)) { throw "Root pom.xml missing after import" }
    if (-not (Get-Command mvn -ErrorAction SilentlyContinue)) { throw "Maven (mvn) not found in PATH" }

    Push-Location $stage
    try {
        Write-Host "BUILD: mvn -DskipTests package"
        & mvn -DskipTests package 2>&1 | Tee-Object -FilePath $buildLog
        $buildCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($buildCode -ne 0) { throw "Maven build failed with exit code $buildCode" }
    Write-Host "BUILD OK"

    "RelativePath`tLength`tLastWriteTimeUtc`tSHA256" | Set-Content -LiteralPath $manifest -Encoding UTF8
    Get-ChildItem -LiteralPath $stage -File -Recurse -Force |
        Where-Object { $_.Extension.ToLowerInvariant() -notin @('.jpg','.jpeg','.png','.gif','.webp','.bmp') } |
        Sort-Object FullName |
        ForEach-Object {
            $relative = $_.FullName.Substring($stage.Length).TrimStart('\')
            $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
            "$relative`t$($_.Length)`t$($_.LastWriteTimeUtc.ToString('o'))`t$hash" | Add-Content -LiteralPath $manifest -Encoding UTF8
        }
    Write-Host "MANIFEST: $manifest"
    Write-Host "STAGE READY: $stage"
} catch {
    Write-Host "ABORTED: $($_.Exception.Message)"
    throw
} finally {
    Stop-Transcript
}

Write-Host "RUN LOG: $runLog"
