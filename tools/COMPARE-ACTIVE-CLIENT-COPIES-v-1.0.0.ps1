[CmdletBinding()]
param(
    [string]$InstallRoot = 'J:\mtg\xmage',
    [string[]]$SearchRoots = @('J:\mtg', 'J:\xmage repositorio'),
    [string]$LogRoot = 'J:\mtg\_LOGS'
)

$ErrorActionPreference = 'Stop'
$runId = Get-Date -Format 'yyyyMMdd-HHmmss'
$runRoot = Join-Path $LogRoot "COMPARE-ACTIVE-CLIENT-COPIES-v-1.0.0-$runId"
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

$runLog = Join-Path $runRoot 'RUN.log'
$summaryReport = Join-Path $runRoot 'ARCHIVE-SUMMARY.tsv'
$relevantReport = Join-Path $runRoot 'RELEVANT-CLASSES.tsv'
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
        $hex = ([BitConverter]::ToString($sha.Hash)).Replace('-', '')
        return [PSCustomObject]@{
            Length = $Entry.Length
            SHA256 = $hex
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

function Get-MatchState {
    param(
        [hashtable]$ActiveMap,
        [hashtable]$CandidateMap,
        [string]$EntryName
    )

    $active = $ActiveMap[$EntryName]
    $candidate = $CandidateMap[$EntryName]

    if (-not $active -and -not $candidate) { return 'N/A' }
    if (-not $active) { return 'EXTRA_IN_CANDIDATE' }
    if (-not $candidate) { return 'MISSING_IN_CANDIDATE' }
    if ($active.SHA256 -eq $candidate.SHA256 -and $active.Length -eq $candidate.Length) { return 'MATCH' }
    return 'DIFF'
}

$transcriptStarted = $false
try {
    try {
        Start-Transcript -LiteralPath $runLog -Force | Out-Null
        $transcriptStarted = $true
    }
    catch {
        throw "RUN LOG could not be started: $($_.Exception.Message)"
    }

    if (-not (Test-Path -LiteralPath $runLog -PathType Leaf)) {
        throw "RUN LOG was not created: $runLog"
    }

    Write-Host 'COMPARE ACTIVE CLIENT COPIES v1.0.0'
    Write-Host "Started: $(Get-Date -Format o)"
    Write-Host "InstallRoot: $InstallRoot"
    Write-Host "SearchRoots: $($SearchRoots -join '; ')"
    Write-Host 'READ-ONLY: no JAR, source, installation, or image file is modified'
    Write-Host 'SCOPE: exact mage-client-1.4.61.jar copies; class/resource fingerprints only'

    $activeJar = Join-Path $InstallRoot 'client\lib\mage-client-1.4.61.jar'
    if (-not (Test-Path -LiteralPath $activeJar -PathType Leaf)) {
        throw "Active client JAR not found: $activeJar"
    }

    $activeJarHash = (Get-FileHash -LiteralPath $activeJar -Algorithm SHA256).Hash
    Write-Host "ACTIVE JAR: $activeJar"
    Write-Host "ACTIVE JAR SHA256: $activeJarHash"

    # Windows PowerShell can pass a comma-separated array parameter as one string
    # when this script is launched through powershell.exe -File. Normalize it
    # before scanning so every requested root is actually visited.
    $effectiveSearchRoots = New-Object System.Collections.Generic.List[string]
    foreach ($rawRoot in $SearchRoots) {
        foreach ($rootPart in ($rawRoot -split ',')) {
            $root = $rootPart.Trim()
            if ($root.Length -eq 0) { continue }
            if (-not $effectiveSearchRoots.Contains($root)) {
                [void]$effectiveSearchRoots.Add($root)
            }
        }
    }

    Write-Host "SearchRoots: $($effectiveSearchRoots -join '; ')"

    $candidatePaths = New-Object System.Collections.Generic.List[string]
    foreach ($root in $effectiveSearchRoots) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) {
            Write-Host "SEARCH ROOT MISSING: $root"
            continue
        }

        Write-Host "SEARCH ROOT OK: $root"
        Get-ChildItem -LiteralPath $root -Recurse -File -Force -Filter 'mage-client-1.4.61.jar' -ErrorAction SilentlyContinue |
            ForEach-Object {
                if (-not $candidatePaths.Contains($_.FullName)) {
                    $candidatePaths.Add($_.FullName)
                }
            }
    }

    if (-not $candidatePaths.Contains($activeJar)) {
        $candidatePaths.Add($activeJar)
    }

    $candidatePaths = @($candidatePaths | Sort-Object -Unique)
    Write-Host "JAR COPIES FOUND: $($candidatePaths.Count)"

    $activeMap = Get-JarEntryMap -Path $activeJar
    $classNames = @(
        'mage/client/game/GamePanel.class',
        'mage/client/game/GamePanel$26.class',
        'mage/client/cards/Cards.class',
        'org/mage/card/arcane/CardPanelRenderModeImage.class',
        'org/mage/card/arcane/CardPanelRenderModeImage$1.class',
        'org/mage/card/arcane/CardRenderer.class',
        'org/mage/plugins/card/CardPluginImpl.class',
        'mage/client/plugins/adapters/MageActionCallback.class',
        'icon-mage.ico'
    )

    $summaryRows = New-Object System.Collections.Generic.List[object]
    $relevantRows = New-Object System.Collections.Generic.List[object]

    foreach ($candidatePath in $candidatePaths) {
        Write-Host "COMPARE: $candidatePath"
        try {
            $candidateFileHash = (Get-FileHash -LiteralPath $candidatePath -Algorithm SHA256).Hash
            $candidateMap = Get-JarEntryMap -Path $candidatePath
            $allNames = @($activeMap.Keys + $candidateMap.Keys) |
                Where-Object { $_ -ne 'META-INF/MANIFEST.MF' } |
                Sort-Object -Unique
            $allDifferent = 0
            foreach ($name in $allNames) {
                $a = $activeMap[$name]
                $b = $candidateMap[$name]
                if (-not $a -or -not $b -or $a.SHA256 -ne $b.SHA256 -or $a.Length -ne $b.Length) {
                    $allDifferent++
                }
            }

            $classUnion = @($activeMap.Keys + $candidateMap.Keys) |
                Where-Object { $_ -like '*.class' } |
                Sort-Object -Unique
            $classDifferent = 0
            $classMissing = 0
            $classExtra = 0
            foreach ($name in $classUnion) {
                $a = $activeMap[$name]
                $b = $candidateMap[$name]
                if (-not $a) {
                    $classExtra++
                } elseif (-not $b) {
                    $classMissing++
                } elseif ($a.SHA256 -ne $b.SHA256 -or $a.Length -ne $b.Length) {
                    $classDifferent++
                }
            }

            $file = Get-Item -LiteralPath $candidatePath
            $row = [ordered]@{
                Role = if ($candidateFileHash -eq $activeJarHash) { 'EXACT_ACTIVE_SHA256' } else { 'OTHER_COPY' }
                FullName = $candidatePath
                Length = $file.Length
                LastWriteTime = $file.LastWriteTime.ToString('o')
                SHA256 = $candidateFileHash
                AllEntriesDifferent = $allDifferent
                ClassDifferent = $classDifferent
                ClassMissing = $classMissing
                ClassExtra = $classExtra
            }
            foreach ($className in $classNames) {
                $propertyName = ($className -replace '[^A-Za-z0-9]', '_').Trim('_')
                $row[$propertyName] = Get-MatchState -ActiveMap $activeMap -CandidateMap $candidateMap -EntryName $className
                $relevantRows.Add([PSCustomObject]@{
                    Candidate = $candidatePath
                    Entry = $className
                    State = Get-MatchState -ActiveMap $activeMap -CandidateMap $candidateMap -EntryName $className
                    ActiveLength = if ($activeMap[$className]) { $activeMap[$className].Length } else { '' }
                    CandidateLength = if ($candidateMap[$className]) { $candidateMap[$className].Length } else { '' }
                    ActiveSHA256 = if ($activeMap[$className]) { $activeMap[$className].SHA256 } else { '' }
                    CandidateSHA256 = if ($candidateMap[$className]) { $candidateMap[$className].SHA256 } else { '' }
                })
            }
            $summaryRows.Add([PSCustomObject]$row)
        }
        catch {
            Write-Host "JAR COMPARE ERROR: $($_.Exception.Message)"
            $summaryRows.Add([PSCustomObject]@{
                Role = 'ERROR'
                FullName = $candidatePath
                Length = ''
                LastWriteTime = ''
                SHA256 = ''
                AllEntriesDifferent = ''
                ClassDifferent = ''
                ClassMissing = ''
                ClassExtra = ''
            })
        }
    }

    $summaryRows = @($summaryRows | Sort-Object @{Expression={ if ($_.Role -eq 'EXACT_ACTIVE_SHA256') { 0 } else { 1 } }}, ClassDifferent, AllEntriesDifferent, FullName)
    $relevantRows = @($relevantRows | Sort-Object Candidate, Entry)

    $summaryRows | Export-Csv -LiteralPath $summaryReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8
    $relevantRows | Export-Csv -LiteralPath $relevantReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

    Write-Host ''
    Write-Host '[CLOSEST COPIES]'
    $summaryRows | Select-Object Role,ClassDifferent,ClassMissing,ClassExtra,AllEntriesDifferent,FullName | Format-Table -AutoSize

    @(
        'COMPARE ACTIVE CLIENT COPIES v1.0.0'
        "Finished: $(Get-Date -Format o)"
        "Active JAR: $activeJar"
        "Active SHA256: $activeJarHash"
        "JAR copies analyzed: $($candidatePaths.Count)"
        "Run log: $runLog"
        "Summary report: $summaryReport"
        "Relevant classes report: $relevantReport"
        'Read-only operation. No JAR, source, installation, or card image was modified.'
        'Interpretation: ClassDifferent=0 means all class entries match the active client JAR.'
    ) | Set-Content -LiteralPath $readme -Encoding UTF8

    Write-Host ''
    Write-Host 'RESULT: active client copy comparison completed'
    Write-Host "RUN LOG: $runLog"
    Write-Host "SUMMARY REPORT: $summaryReport"
    Write-Host "RELEVANT REPORT: $relevantReport"
    Write-Host "README: $readme"
}
catch {
    Write-Host "ABORTED: $($_.Exception.Message)"
    throw
}
finally {
    if ($transcriptStarted) {
        Stop-Transcript | Out-Null
    }
}
