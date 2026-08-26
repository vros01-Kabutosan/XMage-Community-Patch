[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$CandidateSourceRoot,

    [string]$InstallRoot = 'J:\mtg\xmage',
    [string]$ArchiveRoot = 'J:\mtg\_ARCHIVO',
    [string]$LogRoot = 'J:\mtg\_LOGS',
    [string]$MavenCommand = ''
)

$ErrorActionPreference = 'Stop'
$runId = Get-Date -Format 'yyyyMMdd-HHmmss'
$runName = "SOURCE-CANDIDATE-LINEAGE-v-1.0.0-$runId"
$stageRoot = Join-Path $ArchiveRoot $runName
$runRoot = Join-Path $LogRoot $runName

New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

$runLog = Join-Path $runRoot 'RUN.log'
$mavenLog = Join-Path $runRoot 'MAVEN.log'
$resultReport = Join-Path $runRoot 'RESULT.tsv'
$familyReport = Join-Path $runRoot 'CLASS-FAMILIES.tsv'
$readme = Join-Path $runRoot 'README.txt'

Add-Type -AssemblyName System.IO.Compression.FileSystem

function Get-EntryFingerprint {
    param([System.IO.Compression.ZipArchiveEntry]$Entry)

    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = $null
    try {
        $stream = $Entry.Open()
        $buffer = New-Object byte[] 1048576
        while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
            [void]$sha.TransformBlock($buffer, 0, $read, $buffer, 0)
        }
        [void]$sha.TransformFinalBlock($buffer, 0, 0)
        return [PSCustomObject]@{
            Length = $Entry.Length
            SHA256 = ([BitConverter]::ToString($sha.Hash)).Replace('-', '')
        }
    }
    finally {
        if ($stream) { $stream.Dispose() }
        $sha.Dispose()
    }
}

function Get-JarEntryMap {
    param([string]$Path)

    $map = @{}
    $archive = [System.IO.Compression.ZipFile]::OpenRead($Path)
    try {
        foreach ($entry in $archive.Entries) {
            if (-not $entry.FullName.EndsWith('/')) {
                $map[$entry.FullName] = Get-EntryFingerprint -Entry $entry
            }
        }
    }
    finally {
        $archive.Dispose()
    }
    return $map
}

function Get-State {
    param(
        [hashtable]$ActiveMap,
        [hashtable]$CandidateMap,
        [string]$Name
    )

    $active = $ActiveMap[$Name]
    $candidate = $CandidateMap[$Name]

    if (-not $active -and -not $candidate) { return 'N/A' }
    if (-not $active) { return 'EXTRA_IN_CANDIDATE' }
    if (-not $candidate) { return 'MISSING_IN_CANDIDATE' }
    if ($active.Length -eq $candidate.Length -and $active.SHA256 -eq $candidate.SHA256) {
        return 'MATCH'
    }
    return 'DIFF'
}

function Get-FullPath {
    param([string]$Path)
    return [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
}

$transcriptStarted = $false
$exitCode = 1
$status = 'NOT_STARTED'
$errorMessage = ''
$builtJar = ''
$activeJar = Join-Path $InstallRoot 'client\lib\mage-client-1.4.61.jar'
$activeJarHash = ''

$families = @(
    [PSCustomObject]@{ Component = 'GamePanel'; Prefix = 'mage/client/game/GamePanel' },
    [PSCustomObject]@{ Component = 'Cards'; Prefix = 'mage/client/cards/Cards' },
    [PSCustomObject]@{ Component = 'CardPanelRenderModeImage'; Prefix = 'org/mage/card/arcane/CardPanelRenderModeImage' },
    [PSCustomObject]@{ Component = 'CardRenderer'; Prefix = 'org/mage/card/arcane/CardRenderer' },
    [PSCustomObject]@{ Component = 'CardPluginImpl'; Prefix = 'org/mage/plugins/card/CardPluginImpl' },
    [PSCustomObject]@{ Component = 'MageActionCallback'; Prefix = 'mage/client/plugins/adapters/MageActionCallback' }
)

try {
    Start-Transcript -LiteralPath $runLog -Force | Out-Null
    $transcriptStarted = $true

    if (-not (Test-Path -LiteralPath $runLog -PathType Leaf)) {
        throw "RUN LOG was not created: $runLog"
    }

    $candidateFull = Get-FullPath $CandidateSourceRoot
    $installFull = Get-FullPath $InstallRoot

    Write-Host 'SOURCE CANDIDATE LINEAGE BUILD v1.0.0'
    Write-Host "Started: $(Get-Date -Format o)"
    Write-Host "CandidateSourceRoot: $candidateFull"
    Write-Host "StageRoot: $stageRoot"
    Write-Host "InstallRoot: $installFull"
    Write-Host 'READ-ONLY: active installation and original source are never modified'
    Write-Host 'COPY POLICY: isolated stage only; no /MIR; generated target/.git directories excluded'
    Write-Host 'IMAGE POLICY: card-art directories excluded; no card image payload is required or copied'

    if (-not (Test-Path -LiteralPath $candidateFull -PathType Container)) {
        throw "Candidate source root not found: $candidateFull"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $candidateFull 'pom.xml') -PathType Leaf)) {
        throw "Candidate source root has no pom.xml: $candidateFull"
    }
    if (-not (Test-Path -LiteralPath $activeJar -PathType Leaf)) {
        throw "Active client JAR not found: $activeJar"
    }

    if ($candidateFull -eq $installFull -or $candidateFull.StartsWith($installFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Safety stop: candidate source is inside the active installation'
    }

    $activeJarHash = (Get-FileHash -LiteralPath $activeJar -Algorithm SHA256).Hash
    Write-Host "ACTIVE CLIENT JAR SHA256: $activeJarHash"

    # Exclude only generated Maven targets. A source package named
    # mage\target is legitimate Java source and must never be excluded.
    $excludedDirs = New-Object System.Collections.Generic.List[string]

    Get-ChildItem -LiteralPath $candidateFull -Directory -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq 'target' -and
            (Test-Path -LiteralPath (Join-Path $_.Parent.FullName 'pom.xml') -PathType Leaf)
        } |
        ForEach-Object {
            if (-not $excludedDirs.Contains($_.FullName)) {
                [void]$excludedDirs.Add($_.FullName)
            }
        }

    Get-ChildItem -LiteralPath $candidateFull -Directory -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq '.git' } |
        ForEach-Object {
            if (-not $excludedDirs.Contains($_.FullName)) {
                [void]$excludedDirs.Add($_.FullName)
            }
        }

    foreach ($relativeImageDir in @(
        'plugins\images',
        'card-images',
        'card_images',
        'card-art',
        'card_art'
    )) {
        $imageDir = Join-Path $candidateFull $relativeImageDir
        if (Test-Path -LiteralPath $imageDir -PathType Container) {
            if (-not $excludedDirs.Contains($imageDir)) {
                [void]$excludedDirs.Add($imageDir)
            }
        }
    }

    Write-Host 'COPY: candidate source to isolated stage'
    $copyArgs = @(
        $candidateFull,
        $stageRoot,
        '/E',
        '/COPY:DAT',
        '/DCOPY:DAT',
        '/XJ',
        '/R:1',
        '/W:1',
        '/NP'
    )
    if ($excludedDirs.Count -gt 0) {
        $copyArgs += '/XD'
        $copyArgs += @($excludedDirs)
    }

    & robocopy @copyArgs 2>&1 | ForEach-Object { Write-Host $_ }
    $copyCode = $LASTEXITCODE
    if ($copyCode -ge 8) {
        throw "Robocopy failed with exit code $copyCode"
    }
    Write-Host "COPY OK: robocopy exit $copyCode"

    $resolvedMaven = $MavenCommand
    if ([string]::IsNullOrWhiteSpace($resolvedMaven)) {
        $wrapper = Join-Path $stageRoot 'mvnw.cmd'
        if (Test-Path -LiteralPath $wrapper -PathType Leaf) {
            $resolvedMaven = $wrapper
        }
    }

    if ([string]::IsNullOrWhiteSpace($resolvedMaven)) {
        $knownMaven = @(
            'J:\xmage repositorio\XMage-Community-Patch-hardening-update-architecture\tools\migration\migration-workspace\port-1.4.61V1\tools\apache-maven-3.9.16\bin\mvn.cmd',
            'J:\xmage repositorio\XMage-Community-Patch-hardening-update-architecture\tools\apache-maven-3.9.9\bin\mvn.cmd',
            'J:\mtg\_ARCHIVO\30-HERRAMIENTAS\apache-maven-3.9.9\bin\mvn.cmd'
        )
        $resolvedMaven = $knownMaven | Where-Object {
            Test-Path -LiteralPath $_ -PathType Leaf
        } | Select-Object -First 1
    }

    if ([string]::IsNullOrWhiteSpace($resolvedMaven)) {
        $pathMaven = Get-Command mvn.cmd -ErrorAction SilentlyContinue
        if ($pathMaven) {
            $resolvedMaven = $pathMaven.Source
        }
    }

    if ([string]::IsNullOrWhiteSpace($resolvedMaven)) {
        $pathMaven = Get-Command mvn -ErrorAction SilentlyContinue
        if ($pathMaven) {
            $resolvedMaven = $pathMaven.Source
        }
    }

    if ([string]::IsNullOrWhiteSpace($resolvedMaven)) {
        throw 'Maven not found. Pass -MavenCommand with the verified mvn.cmd path.'
    }

    Write-Host "MAVEN: $resolvedMaven"
    Write-Host 'BUILD: Mage.Client only, with required modules, tests skipped'
    Push-Location $stageRoot
    try {
        & $resolvedMaven -B -ntp -pl Mage.Client -am package -DskipTests 2>&1 |
            Tee-Object -LiteralPath $mavenLog |
            ForEach-Object { Write-Host $_ }
        $buildCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    if ($buildCode -ne 0) {
        $status = 'BUILD_FAILED'
        $errorMessage = "Maven build failed with exit code $buildCode"
        Write-Host "ABORTED: $errorMessage"
    }
    else {
        $builtJar = Join-Path $stageRoot 'Mage.Client\target\mage-client-1.4.61.jar'
        if (-not (Test-Path -LiteralPath $builtJar -PathType Leaf)) {
            $builtJar = Get-ChildItem -LiteralPath $stageRoot -Recurse -File -Force -Filter 'mage-client-1.4.61.jar' |
                Where-Object { $_.FullName -match '\\target\\' } |
                Select-Object -ExpandProperty FullName -First 1
        }
        if ([string]::IsNullOrWhiteSpace($builtJar) -or -not (Test-Path -LiteralPath $builtJar -PathType Leaf)) {
            throw 'Maven reported success but the Mage.Client JAR was not found'
        }

        $builtJarHash = (Get-FileHash -LiteralPath $builtJar -Algorithm SHA256).Hash
        Write-Host "BUILT CLIENT JAR: $builtJar"
        Write-Host "BUILT CLIENT JAR SHA256: $builtJarHash"

        $activeMap = Get-JarEntryMap -Path $activeJar
        $candidateMap = Get-JarEntryMap -Path $builtJar

        $allClassNames = @($activeMap.Keys + $candidateMap.Keys) |
            Where-Object { $_ -like '*.class' } |
            Sort-Object -Unique

        $classMatches = 0
        $classDiffs = 0
        $classMissing = 0
        $classExtra = 0

        foreach ($name in $allClassNames) {
            $state = Get-State -ActiveMap $activeMap -CandidateMap $candidateMap -Name $name
            if ($state -eq 'MATCH') { $classMatches++ }
            elseif ($state -eq 'DIFF') { $classDiffs++ }
            elseif ($state -eq 'MISSING_IN_CANDIDATE') { $classMissing++ }
            elseif ($state -eq 'EXTRA_IN_CANDIDATE') { $classExtra++ }
        }

        $familyRows = New-Object System.Collections.Generic.List[object]
        foreach ($family in $families) {
            $names = @($activeMap.Keys + $candidateMap.Keys) |
                Where-Object {
                    $_.StartsWith($family.Prefix) -and $_ -like '*.class'
                } |
                Sort-Object -Unique

            $matches = 0
            $diffs = 0
            $missing = 0
            $extra = 0

            foreach ($name in $names) {
                $state = Get-State -ActiveMap $activeMap -CandidateMap $candidateMap -Name $name
                if ($state -eq 'MATCH') { $matches++ }
                elseif ($state -eq 'DIFF') { $diffs++ }
                elseif ($state -eq 'MISSING_IN_CANDIDATE') { $missing++ }
                elseif ($state -eq 'EXTRA_IN_CANDIDATE') { $extra++ }
            }

            $familyRows.Add([PSCustomObject]@{
                Component = $family.Component
                Prefix = $family.Prefix
                Entries = $names.Count
                Matches = $matches
                Differences = $diffs
                Missing = $missing
                Extra = $extra
                Result = if ($diffs -eq 0 -and $missing -eq 0 -and $extra -eq 0) { 'EXACT_FAMILY_MATCH' } else { 'NOT_EXACT' }
            })
        }

        $familyRows | Export-Csv -LiteralPath $familyReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

        $status = if ($classDiffs -eq 0 -and $classMissing -eq 0 -and $classExtra -eq 0) {
            'EXACT_CLIENT_CLASS_MATCH'
        }
        else {
            'CLIENT_CLASS_MISMATCH'
        }

        $result = [PSCustomObject][ordered]@{
            Status = $status
            CandidateSourceRoot = $candidateFull
            StageRoot = $stageRoot
            ActiveJar = $activeJar
            BuiltJar = $builtJar
            ActiveJarSHA256 = $activeJarHash
            BuiltJarSHA256 = $builtJarHash
            ClassMatches = $classMatches
            ClassDifferences = $classDiffs
            ClassMissing = $classMissing
            ClassExtra = $classExtra
            RunLog = $runLog
            MavenLog = $mavenLog
            FamilyReport = $familyReport
        }
        $result | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

        Write-Host ''
        Write-Host '[CLASS FAMILY RESULTS]'
        $familyRows | Format-Table -AutoSize

        $exitCode = if ($status -eq 'EXACT_CLIENT_CLASS_MATCH') { 0 } else { 2 }
    }

    if (-not (Test-Path -LiteralPath $resultReport -PathType Leaf)) {
        $failedResult = [PSCustomObject][ordered]@{
            Status = $status
            CandidateSourceRoot = $candidateFull
            StageRoot = $stageRoot
            ActiveJar = $activeJar
            BuiltJar = $builtJar
            ActiveJarSHA256 = $activeJarHash
            BuiltJarSHA256 = ''
            ClassMatches = ''
            ClassDifferences = ''
            ClassMissing = ''
            ClassExtra = ''
            Error = $errorMessage
            RunLog = $runLog
            MavenLog = $mavenLog
            FamilyReport = $familyReport
        }
        $failedResult | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8
    }

    @(
        'SOURCE CANDIDATE LINEAGE BUILD v1.0.0'
        "Finished: $(Get-Date -Format o)"
        "Status: $status"
        "Candidate source: $candidateFull"
        "Stage: $stageRoot"
        "Active client JAR: $activeJar"
        "Active client SHA256: $activeJarHash"
        "Built client JAR: $builtJar"
        "Run log: $runLog"
        "Maven log: $mavenLog"
        "Result report: $resultReport"
        "Class family report: $familyReport"
        'Original source and active installation were not modified.'
        'No /MIR was used.'
        'Card-art directories were excluded; card images are outside this lineage test.'
        'Interpretation: exact client source provenance requires an exact class-family match, not only a successful Maven build.'
    ) | Set-Content -LiteralPath $readme -Encoding UTF8

    Write-Host ''
    Write-Host "RESULT: $status"
    Write-Host "RUN LOG: $runLog"
    Write-Host "RESULT REPORT: $resultReport"
    Write-Host "FAMILY REPORT: $familyReport"
    Write-Host "README: $readme"
}
catch {
    $status = 'ABORTED'
    $errorMessage = $_.Exception.Message
    Write-Host "ABORTED: $errorMessage"

    try {
        if (-not (Test-Path -LiteralPath $resultReport -PathType Leaf)) {
            [PSCustomObject][ordered]@{
                Status = $status
                CandidateSourceRoot = $CandidateSourceRoot
                StageRoot = $stageRoot
                ActiveJar = $activeJar
                BuiltJar = $builtJar
                ActiveJarSHA256 = $activeJarHash
                BuiltJarSHA256 = ''
                Error = $errorMessage
                RunLog = $runLog
                MavenLog = $mavenLog
                FamilyReport = $familyReport
            } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8
        }
        @(
            'SOURCE CANDIDATE LINEAGE BUILD v1.0.0'
            "Finished: $(Get-Date -Format o)"
            "Status: $status"
            "Error: $errorMessage"
            "Run log: $runLog"
            "Result report: $resultReport"
            'No installation or original source was modified.'
        ) | Set-Content -LiteralPath $readme -Encoding UTF8
    }
    catch {
        Write-Host "REPORT WRITE ERROR: $($_.Exception.Message)"
    }
}
finally {
    if ($transcriptStarted) {
        Stop-Transcript | Out-Null
    }
}

if ($exitCode -ne 0) {
    exit $exitCode
}
