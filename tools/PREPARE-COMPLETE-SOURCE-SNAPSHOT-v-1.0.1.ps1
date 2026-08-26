[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$StageRoot,

    [Parameter(Mandatory = $true)]
    [string]$RepositoryRoot,

    [Parameter(Mandatory = $true)]
    [string]$ArchiveRoot,

    [Parameter(Mandatory = $true)]
    [string]$LogRoot,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9]{64}$')]
    [string]$ExpectedSuperiorSHA256,

    [string]$SourceRelativePath = 'source/xmage/1.4.61V1-community-patch-v-1',
    [string]$ManifestRelativePath = 'manifests/1.4.61V1-community-patch-v-1/SOURCE-MANIFEST.tsv',
    [string]$ReadmeRelativePath = 'manifests/1.4.61V1-community-patch-v-1/README.txt'
)

$ErrorActionPreference = 'Stop'

function Get-FullPath {
    param([string]$Path)
    $full = [System.IO.Path]::GetFullPath($Path)
    if ($full.Length -gt 3) { $full = $full.TrimEnd('\') }
    return $full
}

function Test-IsUnder {
    param([string]$Child, [string]$Parent)
    return $Child.Equals($Parent, [System.StringComparison]::OrdinalIgnoreCase) -or
        $Child.StartsWith($Parent + '\', [System.StringComparison]::OrdinalIgnoreCase)
}

function Add-UniquePath {
    param(
        [System.Collections.Generic.List[string]]$List,
        [string]$Path
    )
    $full = Get-FullPath $Path
    if (-not $List.Contains($full)) { [void]$List.Add($full) }
}

$runId = Get-Date -Format 'yyyyMMdd-HHmmss'
$runName = "PREPARE-COMPLETE-SOURCE-SNAPSHOT-v-1.0.1-$runId"
$runRoot = Join-Path $LogRoot $runName
$runLog = Join-Path $runRoot 'RUN.log'
$resultReport = Join-Path $runRoot 'RESULT.tsv'
$localReadme = Join-Path $runRoot 'README.txt'

$transcriptStarted = $false
$status = 'NOT_STARTED'
$errorMessage = ''
$exitCode = 1
$branch = ''
$sourceDestFull = ''
$manifestFull = ''
$repoReadmeFull = ''
$superiorHash = ''
$fileCount = 0
$sourceLikeFileCount = 0
$totalBytes = 0
$robocopyExit = ''

try {
    New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
    Start-Transcript -LiteralPath $runLog -Force | Out-Null
    $transcriptStarted = $true

    $stageFull = Get-FullPath $StageRoot
    $repoFull = Get-FullPath $RepositoryRoot
    $archiveFull = Get-FullPath $ArchiveRoot
    $expectedHash = $ExpectedSuperiorSHA256.ToUpperInvariant()

    Write-Host 'PREPARE COMPLETE SOURCE SNAPSHOT v1.0.1'
    Write-Host "Started: $(Get-Date -Format o)"
    Write-Host "StageRoot: $stageFull"
    Write-Host "RepositoryRoot: $repoFull"
    Write-Host "SourceRelativePath: $SourceRelativePath"
    Write-Host 'READ-ONLY: active installation and protected bases are not modified'
    Write-Host 'COPY POLICY: new destination only; no /MIR; generated target/.git excluded'
    Write-Host 'IMAGE POLICY: card-art directories excluded'
    Write-Host 'GIT POLICY: this tool never commits or pushes'

    if (-not (Test-Path -LiteralPath $stageFull -PathType Container)) {
        throw "Stage root not found: $stageFull"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $stageFull 'pom.xml') -PathType Leaf)) {
        throw "Stage root has no root pom.xml: $stageFull"
    }
    if (-not (Test-Path -LiteralPath $repoFull -PathType Container)) {
        throw "Repository root not found: $repoFull"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $repoFull '.git'))) {
        throw "Repository root has no .git: $repoFull"
    }
    if (-not (Test-IsUnder -Child $stageFull -Parent $archiveFull)) {
        throw 'Safety stop: StageRoot must be inside ArchiveRoot'
    }
    if ($stageFull -match '(?i)\\(PRIVADO-BLINDADO-XMAGE|RC1\.1-COMPLETA-PORTABLE)(\\|$)') {
        throw 'Safety stop: protected base cannot be used as StageRoot'
    }

    if (-not (Get-Command git.exe -ErrorAction SilentlyContinue) -and
        -not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw 'Git was not found in PATH'
    }

    $branch = (& git -C $repoFull branch --show-current 2>&1 | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($branch)) {
        throw 'Safety stop: detached HEAD is not allowed'
    }
    if ($branch -match '^(main|master|protected/|stable/|release/)') {
        throw "Safety stop: protected/stable branch is not allowed: $branch"
    }
    Write-Host "Git branch: $branch"

    $sourceDestFull = Get-FullPath (Join-Path $repoFull $SourceRelativePath)
    $manifestFull = Get-FullPath (Join-Path $repoFull $ManifestRelativePath)
    $repoReadmeFull = Get-FullPath (Join-Path $repoFull $ReadmeRelativePath)

    if (-not (Test-IsUnder -Child $sourceDestFull -Parent $repoFull) -or
        $sourceDestFull.Equals($repoFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Safety stop: source destination is outside the repository'
    }
    if (Test-Path -LiteralPath $sourceDestFull) {
        throw "Safety stop: destination already exists; no overwrite or merge is allowed: $sourceDestFull"
    }
    if (Test-Path -LiteralPath $manifestFull) {
        throw "Safety stop: manifest destination already exists: $manifestFull"
    }
    if (Test-Path -LiteralPath $repoReadmeFull) {
        throw "Safety stop: README destination already exists: $repoReadmeFull"
    }

    $stageSuperior = @(Get-ChildItem -LiteralPath $stageFull -Recurse -File -Force -Filter 'SuperiorSpiderMan.java' |
        Where-Object { $_.FullName -notmatch '\\target\\|\\.git\\' })
    if ($stageSuperior.Count -ne 1) {
        throw "Safety stop: expected exactly one non-generated SuperiorSpiderMan.java, found $($stageSuperior.Count)"
    }

    $superiorHash = (Get-FileHash -LiteralPath $stageSuperior[0].FullName -Algorithm SHA256).Hash.ToUpperInvariant()
    Write-Host "SUPERIOR SOURCE FOUND: $($stageSuperior[0].FullName)"
    Write-Host "SUPERIOR SHA256: $superiorHash"
    if ($superiorHash -ne $expectedHash) {
        throw "Safety stop: Superior Spider-Man hash mismatch: $superiorHash"
    }

    $excludedDirs = New-Object System.Collections.Generic.List[string]

    Get-ChildItem -LiteralPath $stageFull -Directory -Recurse -Force -ErrorAction Stop |
        Where-Object {
            $_.Name -eq 'target' -and
            (Test-Path -LiteralPath (Join-Path $_.Parent.FullName 'pom.xml') -PathType Leaf)
        } |
        ForEach-Object {
            Add-UniquePath -List $excludedDirs -Path $_.FullName
        }

    Get-ChildItem -LiteralPath $stageFull -Directory -Recurse -Force -ErrorAction Stop |
        Where-Object { $_.Name -eq '.git' } |
        ForEach-Object {
            Add-UniquePath -List $excludedDirs -Path $_.FullName
        }

    foreach ($relativeImageDir in @(
        'plugins\images',
        'card-images',
        'card_images',
        'card-art',
        'card_art'
    )) {
        $imageDir = Join-Path $stageFull $relativeImageDir
        if (Test-Path -LiteralPath $imageDir -PathType Container) {
            Add-UniquePath -List $excludedDirs -Path $imageDir
        }
    }

    New-Item -ItemType Directory -Force -Path $sourceDestFull | Out-Null

    $copyArgs = @(
        $stageFull,
        $sourceDestFull,
        '/E', '/COPY:DAT', '/DCOPY:DAT', '/XJ',
        '/R:1', '/W:1', '/NP', '/NFL', '/NDL'
    )
    if ($excludedDirs.Count -gt 0) {
        $copyArgs += '/XD'
        foreach ($excludedDir in $excludedDirs) { $copyArgs += $excludedDir }
    }

    Write-Host "Excluded directories: $($excludedDirs.Count)"
    $copyOutput = & robocopy @copyArgs 2>&1
    $copyOutput | ForEach-Object { Write-Host $_ }
    $robocopyExit = $LASTEXITCODE
    Write-Host "ROBOCOPY EXIT: $robocopyExit"
    if ($robocopyExit -ge 8) {
        throw "Robocopy failed with exit code $robocopyExit"
    }

    $generatedTargets = @(Get-ChildItem -LiteralPath $sourceDestFull -Directory -Recurse -Force -ErrorAction Stop |
        Where-Object {
            $_.Name -eq 'target' -and
            (Test-Path -LiteralPath (Join-Path $_.Parent.FullName 'pom.xml') -PathType Leaf)
        })
    $gitDirs = @(Get-ChildItem -LiteralPath $sourceDestFull -Directory -Recurse -Force -ErrorAction Stop |
        Where-Object { $_.Name -eq '.git' })

    if ($generatedTargets.Count -ne 0) {
        throw "Safety stop: generated target directories copied: $($generatedTargets.Count)"
    }
    if ($gitDirs.Count -ne 0) {
        throw "Safety stop: .git directories copied: $($gitDirs.Count)"
    }

    $destinationSuperior = @(Get-ChildItem -LiteralPath $sourceDestFull -Recurse -File -Force -Filter 'SuperiorSpiderMan.java' |
        Where-Object { $_.FullName -notmatch '\\target\\|\\.git\\' })
    if ($destinationSuperior.Count -ne 1) {
        throw "Safety stop: destination contains $($destinationSuperior.Count) SuperiorSpiderMan.java files"
    }

    $destinationSuperiorHash = (Get-FileHash -LiteralPath $destinationSuperior[0].FullName -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($destinationSuperiorHash -ne $expectedHash) {
        throw "Safety stop: destination Superior hash changed during copy: $destinationSuperiorHash"
    }

    $allFiles = @(Get-ChildItem -LiteralPath $sourceDestFull -Recurse -File -Force -ErrorAction Stop)
    $fileCount = $allFiles.Count
    $sourceLikeFileCount = @($allFiles | Where-Object {
        $_.Extension -in @('.java', '.xml', '.properties', '.yml', '.yaml', '.json', '.md', '.txt', '.cmd', '.bat', '.ps1')
    }).Count
    $totalBytes = ($allFiles | Measure-Object -Property Length -Sum).Sum
    if ($null -eq $totalBytes) { $totalBytes = 0 }

    $cardArtFiles = @($allFiles | Where-Object {
        $_.FullName -match '\\plugins\\images\\|\\card-images?\\|\\card[-_]art\\'
    })
    if ($cardArtFiles.Count -ne 0) {
        throw "Safety stop: card-art files copied: $($cardArtFiles.Count)"
    }

    Write-Host "DESTINATION FILES: $fileCount"
    Write-Host "SOURCE-LIKE FILES: $sourceLikeFileCount"
    Write-Host "DESTINATION BYTES: $totalBytes"
    Write-Host "CARD-ART FILES: $($cardArtFiles.Count)"

    $manifestRows = foreach ($file in $allFiles) {
        $relative = $file.FullName.Substring($sourceDestFull.Length).TrimStart('\').Replace('\', '/')
        [PSCustomObject][ordered]@{
            RelativePath = $relative
            Length = $file.Length
            SHA256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToUpperInvariant()
        }
    }

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $manifestFull) | Out-Null
    $manifestRows | Export-Csv -LiteralPath $manifestFull -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

    @(
        'COMPLETE SOURCE SNAPSHOT v1.0.1'
        'Status: prepared for review'
        'Base family: RC1.1 / XMage 1.4.61'
        'Stable Superior Spider-Man source: verified locally'
        'Generated Maven target directories: excluded'
        '.git directories: excluded'
        'Card-art/image payload: excluded'
        'Active installation: never modified'
        'Protected bases: never modified'
        'Copy mode: isolated destination, no /MIR'
        'This tool does not commit or push.'
    ) | Set-Content -LiteralPath $repoReadmeFull -Encoding UTF8

    $status = 'PREPARED_FOR_REVIEW'

    [PSCustomObject][ordered]@{
        Status = $status
        Branch = $branch
        SourceRelativePath = $SourceRelativePath
        ManifestRelativePath = $ManifestRelativePath
        ReadmeRelativePath = $ReadmeRelativePath
        SuperiorSHA256 = $destinationSuperiorHash
        FileCount = $fileCount
        SourceLikeFileCount = $sourceLikeFileCount
        TotalBytes = $totalBytes
        RobocopyExit = $robocopyExit
        NoMirUsed = $true
        ImagesExcluded = $true
        ActiveInstallationModified = $false
        ProtectedBasesModified = $false
        CommitPerformed = $false
        PushPerformed = $false
    } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

    @(
        'PREPARE COMPLETE SOURCE SNAPSHOT v1.0.1'
        "Finished: $(Get-Date -Format o)"
        "Status: $status"
        "Branch: $branch"
        "Source destination: $SourceRelativePath"
        "Manifest: $ManifestRelativePath"
        "Run log: $runLog"
        "Result report: $resultReport"
        "Files: $fileCount"
        'No active installation or protected base was modified.'
        'No /MIR was used.'
        'Card-art/image payload was excluded.'
        'No commit or push was performed.'
    ) | Set-Content -LiteralPath $localReadme -Encoding UTF8

    Write-Host "RESULT: $status"
    Write-Host "RUN LOG: $runLog"
    Write-Host "RESULT REPORT: $resultReport"
    $exitCode = 0
}
catch {
    $status = 'ABORTED'
    $errorMessage = $_.Exception.Message
    Write-Host "ABORTED: $errorMessage"

    try {
        [PSCustomObject][ordered]@{
            Status = $status
            Branch = $branch
            SourceRelativePath = $SourceRelativePath
            ManifestRelativePath = $ManifestRelativePath
            ReadmeRelativePath = $ReadmeRelativePath
            SuperiorSHA256 = $superiorHash
            FileCount = $fileCount
            SourceLikeFileCount = $sourceLikeFileCount
            TotalBytes = $totalBytes
            RobocopyExit = $robocopyExit
            Error = $errorMessage
            ActiveInstallationModified = $false
            ProtectedBasesModified = $false
            CommitPerformed = $false
            PushPerformed = $false
        } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

        @(
            'PREPARE COMPLETE SOURCE SNAPSHOT v1.0.1'
            "Finished: $(Get-Date -Format o)"
            "Status: $status"
            "Error: $errorMessage"
            "Run log: $runLog"
            "Result report: $resultReport"
            'No active installation or protected base was modified.'
        ) | Set-Content -LiteralPath $localReadme -Encoding UTF8
    }
    catch {
        Write-Host "REPORT WRITE ERROR: $($_.Exception.Message)"
    }
}
finally {
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
}

if ($exitCode -ne 0) { exit $exitCode }
