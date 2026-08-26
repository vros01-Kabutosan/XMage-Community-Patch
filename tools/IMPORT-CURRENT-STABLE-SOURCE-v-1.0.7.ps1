[CmdletBinding()]
param(
    [string]$SourceRoot = 'J:\mtg\_ARCHIVO\00-FUENTE\rc1.1-complete-community',
    [string]$SuperiorSource = '',
    [string]$ArchiveRoot = 'J:\mtg\_ARCHIVO',
    [string]$LogRoot = 'J:\mtg\_LOGS',
    [string]$MavenCommand = ''
)

$ErrorActionPreference = 'Stop'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runName = "IMPORT-CURRENT-STABLE-SOURCE-v-1.0.7-$stamp"
$stage = Join-Path $ArchiveRoot $runName
$runLogDir = Join-Path $LogRoot $runName
$runLog = Join-Path $runLogDir 'RUN.log'
$buildLog = Join-Path $runLogDir 'MAVEN-BUILD.log'
$copyLog = Join-Path $runLogDir 'ROBOCOPY.log'
$manifest = Join-Path $runLogDir 'MANIFEST-SHA256.tsv'

New-Item -ItemType Directory -Path $runLogDir -Force | Out-Null
Start-Transcript -Path $runLog -Force

try {
    Write-Host "IMPORT CURRENT STABLE SOURCE v1.0.7"
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
    # Exclude only module-level generated targets. Do not use /XD target by name:
    # the source contains the legitimate Java package mage\target.
    $excludeDirs = @(
        Get-ChildItem -LiteralPath $SourceRoot -Directory -Force |
            ForEach-Object {
                $moduleTarget = Join-Path $_.FullName 'target'
                if (Test-Path -LiteralPath $moduleTarget -PathType Container) { $moduleTarget }
            }
    )
    $sourceGit = Join-Path $SourceRoot '.git'
    if (Test-Path -LiteralPath $sourceGit -PathType Container) { $excludeDirs += $sourceGit }
    Write-Host "EXCLUDE MODULE TARGETS: $($excludeDirs -join '; ')"
    $roboArgs = @($SourceRoot, $stage, '/E', '/XJ', '/R:1', '/W:1', '/COPY:DAT', '/DCOPY:DAT', '/NFL', '/NDL', '/NP')
    if ($excludeDirs.Count -gt 0) { $roboArgs += '/XD'; $roboArgs += $excludeDirs }
    & robocopy @roboArgs 2>&1 |
        Tee-Object -FilePath $copyLog
    $copyCode = $LASTEXITCODE
    if ($copyCode -ge 8) { throw "Robocopy failed with exit code $copyCode" }
    Write-Host "COPY OK: robocopy exit $copyCode"

    $superiorRoot = Join-Path $stage 'Mage.Sets\src'
    $existingSuperior = @(
        Get-ChildItem -LiteralPath $superiorRoot -Recurse -File -Filter 'SuperiorSpiderMan.java' -ErrorAction SilentlyContinue |
            Sort-Object FullName
    )
    Write-Host "SUPERIOR SOURCE COPIES BEFORE INTEGRATION: $($existingSuperior.Count)"
    $existingSuperior | ForEach-Object { Write-Host "  $($_.FullName)" }
    if ($existingSuperior.Count -gt 1) {
        # Prefer the current complete-source layout and remove only duplicate copies
        # inside this newly-created isolated stage.
        $preferred = $existingSuperior |
            Where-Object { $_.FullName -match '\\src\\main\\java\\' } |
            Select-Object -First 1
        if (-not $preferred) { $preferred = $existingSuperior[0] }
        foreach ($duplicate in $existingSuperior) {
            if ($duplicate.FullName -ne $preferred.FullName) {
                Remove-Item -LiteralPath $duplicate.FullName -Force
                Write-Host "REMOVED ISOLATED DUPLICATE: $($duplicate.FullName)"
            }
        }
        $superiorTarget = $preferred.FullName
    } elseif ($existingSuperior.Count -eq 1) {
        $superiorTarget = $existingSuperior[0].FullName
    } else {
        $superiorTarget = Join-Path $stage 'Mage.Sets\src\main\java\mage\cards\s\SuperiorSpiderMan.java'
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $superiorTarget) -Force | Out-Null
    Copy-Item -LiteralPath $SuperiorSource -Destination $superiorTarget -Force
    $superiorHash = (Get-FileHash -LiteralPath $superiorTarget -Algorithm SHA256).Hash
    Write-Host "SUPERIOR INTEGRATED: $superiorHash"
    foreach ($className in @('SuperiorSpiderMan', 'SuperiorSpiderManCopyEffect', 'SuperiorSpiderManCopyApplier')) {
        $declarations = @(
            Get-ChildItem -LiteralPath $superiorRoot -Recurse -File -Filter '*.java' |
                Select-String -Pattern "\bclass\s+$className\b"
        )
        if ($declarations.Count -ne 1) {
            $declarations | ForEach-Object { Write-Host "DUPLICATE CHECK ${className}: $($_.Path):$($_.LineNumber)" }
            throw "Expected exactly one declaration of $className, found $($declarations.Count)"
        }
    }
    Write-Host "SUPERIOR DUPLICATE CHECK: PASS"

    $pom = Join-Path $stage 'pom.xml'
    if (-not (Test-Path -LiteralPath $pom -PathType Leaf)) { throw "Root pom.xml missing after import" }
    $mavenCommand = $MavenCommand
    $projectMavenWrapper = Join-Path $stage 'mvnw.cmd'
    $knownMaven = @(
        'J:\xmage repositorio\XMage-Community-Patch-hardening-update-architecture\tools\migration\migration-workspace\port-1.4.61V1\tools\apache-maven-3.9.16\bin\mvn.cmd',
        'J:\mtg\_ARCHIVO\30-HERRAMIENTAS\apache-maven-3.9.9\bin\mvn.cmd'
    )
    if ($mavenCommand -and -not (Test-Path -LiteralPath $mavenCommand -PathType Leaf)) {
        throw "MavenCommand not found: $mavenCommand"
    }
    if (-not $mavenCommand -and (Test-Path -LiteralPath $projectMavenWrapper -PathType Leaf)) {
        $mavenCommand = $projectMavenWrapper
        Write-Host "MAVEN: project wrapper detected"
    } elseif (-not $mavenCommand) {
        $mavenCommand = $knownMaven | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
        if ($mavenCommand) { Write-Host "MAVEN: deterministic portable Maven detected: $mavenCommand" }
    }
    if (-not $mavenCommand -and (Get-Command mvn.cmd -ErrorAction SilentlyContinue)) {
        $mavenCommand = (Get-Command mvn.cmd).Source
        Write-Host "MAVEN: mvn.cmd detected in PATH"
    } elseif (-not $mavenCommand -and (Get-Command mvn -ErrorAction SilentlyContinue)) {
        $mavenCommand = (Get-Command mvn).Source
        Write-Host "MAVEN: mvn detected in PATH"
    }
    if (-not $mavenCommand) {
        throw "Maven not found: no mvnw.cmd in source and no mvn.cmd/mvn in PATH"
    }

    Push-Location $stage
    try {
        Write-Host "BUILD: mvn -DskipTests package"
        & $mavenCommand -DskipTests package 2>&1 | Tee-Object -FilePath $buildLog
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
