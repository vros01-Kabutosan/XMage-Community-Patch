[CmdletBinding()]
param(
    [string]$InstallRoot = 'J:\mtg\xmage',
    [string[]]$SearchRoots = @('J:\mtg', 'J:\xmage repositorio'),
    [string]$LogRoot = 'J:\mtg\_LOGS'
)

$ErrorActionPreference = 'Stop'
$runId = Get-Date -Format 'yyyyMMdd-HHmmss'
$runRoot = Join-Path $LogRoot "TRACE-ACTIVE-CLIENT-PROVENANCE-v-1.0.0-$runId"
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

$runLog = Join-Path $runRoot 'RUN.log'
$jarReport = Join-Path $runRoot 'JAR-COPIES.tsv'
$sourceReport = Join-Path $runRoot 'SOURCE-CANDIDATES.tsv'
$readme = Join-Path $runRoot 'README.txt'

function Get-SafeHash {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return ''
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Get-RelativeSafePath {
    param(
        [string]$Path,
        [string[]]$Roots
    )
    foreach ($root in $Roots) {
        try {
            $rootFull = [IO.Path]::GetFullPath($root).TrimEnd('\')
            $pathFull = [IO.Path]::GetFullPath($Path)
            if ($pathFull.StartsWith($rootFull + '\', [StringComparison]::OrdinalIgnoreCase)) {
                return $pathFull.Substring($rootFull.Length + 1)
            }
        } catch {
        }
    }
    return $Path
}

$transcriptStarted = $false
try {
    Start-Transcript -LiteralPath $runLog -Force | Out-Null
    $transcriptStarted = $true

    Write-Host 'TRACE ACTIVE CLIENT PROVENANCE v1.0.0'
    Write-Host "Started: $(Get-Date -Format o)"
    Write-Host "InstallRoot: $InstallRoot"
    Write-Host "SearchRoots: $($SearchRoots -join '; ')"
    Write-Host 'READ-ONLY: no installation or source file is modified'
    Write-Host 'CARD IMAGES: not searched or copied'

    if (-not (Test-Path -LiteralPath $InstallRoot -PathType Container)) {
        throw "InstallRoot not found: $InstallRoot"
    }

    $activeClientJar = Join-Path $InstallRoot 'client\lib\mage-client-1.4.61.jar'
    $activeSetsClientJar = Join-Path $InstallRoot 'client\lib\mage-sets-1.4.61.jar'
    $activeServerSetsJar = Join-Path $InstallRoot 'server\lib\mage-sets-1.4.61.jar'

    $activeClientHash = Get-SafeHash $activeClientJar
    $activeSetsClientHash = Get-SafeHash $activeSetsClientJar
    $activeServerSetsHash = Get-SafeHash $activeServerSetsJar

    Write-Host ''
    Write-Host '[ACTIVE INSTALLATION JARS]'
    foreach ($item in @(
        [PSCustomObject]@{ Role = 'active-client'; Path = $activeClientJar; Hash = $activeClientHash },
        [PSCustomObject]@{ Role = 'active-client-mage-sets'; Path = $activeSetsClientJar; Hash = $activeSetsClientHash },
        [PSCustomObject]@{ Role = 'active-server-mage-sets'; Path = $activeServerSetsJar; Hash = $activeServerSetsHash }
    )) {
        if (Test-Path -LiteralPath $item.Path -PathType Leaf) {
            $file = Get-Item -LiteralPath $item.Path
            Write-Host "$($item.Role): $($file.FullName) size=$($file.Length) sha256=$($item.Hash)"
        } else {
            Write-Host "$($item.Role): MISSING $($item.Path)"
        }
    }

    $jarRows = New-Object System.Collections.Generic.List[object]
    $sourceRows = New-Object System.Collections.Generic.List[object]

    $sourceNames = @(
        'GamePanel.java',
        'GamePanel.java.*',
        'Cards.java',
        'Cards.java.*',
        'CardPanelRenderModeImage.java',
        'CardPanelRenderModeImage.java.*',
        'CardRenderer.java',
        'CardRenderer.java.*',
        'CardPluginImpl.java',
        'CardPluginImpl.java.*',
        'MageActionCallback.java',
        'MageActionCallback.java.*',
        'SuperiorSpiderMan.java',
        'SuperiorSpiderMan.java.*'
    )

    foreach ($root in $SearchRoots) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) {
            Write-Host "SEARCH ROOT MISSING: $root"
            continue
        }

        Write-Host "Scanning: $root"

        foreach ($sourcePattern in $sourceNames) {
            Get-ChildItem -LiteralPath $root -Recurse -File -Force -Filter $sourcePattern -ErrorAction SilentlyContinue |
                Where-Object {
                    $path = $_.FullName
                    $path -notmatch '\\target\\' -and
                        $path -notmatch '\\client\\lib\\' -and
                        $path -notmatch '\\server\\lib\\' -and
                        $path -notmatch '\\jre(17)?\\'
                } |
                ForEach-Object {
                    $sourceRows.Add([PSCustomObject]@{
                        FileName = $_.Name
                        FullName = $_.FullName
                        RelativeToSearchRoot = Get-RelativeSafePath -Path $_.FullName -Roots @($root)
                        Length = $_.Length
                        LastWriteTime = $_.LastWriteTime.ToString('o')
                        SHA256 = Get-SafeHash $_.FullName
                    })
                }
        }

        Get-ChildItem -LiteralPath $root -Recurse -File -Force -Filter 'mage-client-1.4.61.jar' -ErrorAction SilentlyContinue |
            Where-Object {
                $_.FullName -notmatch '\\jre(17)?\\'
            } |
            ForEach-Object {
                $hash = Get-SafeHash $_.FullName
                $role = if ($hash -and $hash -eq $activeClientHash) { 'MATCHES_ACTIVE_CLIENT_SHA256' } else { 'OTHER_CLIENT_JAR' }
                $jarRows.Add([PSCustomObject]@{
                    JarName = $_.Name
                    Role = $role
                    FullName = $_.FullName
                    Length = $_.Length
                    LastWriteTime = $_.LastWriteTime.ToString('o')
                    SHA256 = $hash
                })
            }
    }

    $sourceRows = @($sourceRows | Sort-Object FileName, FullName -Unique)
    $jarRows = @($jarRows | Sort-Object SHA256, FullName -Unique)

    Write-Host ''
    Write-Host '[CLIENT JAR COPIES]'
    if ($jarRows.Count -eq 0) {
        Write-Host 'No mage-client-1.4.61.jar copies found under SearchRoots'
    } else {
        $jarRows | Format-Table -AutoSize
    }

    Write-Host ''
    Write-Host '[SOURCE VARIANTS]'
    if ($sourceRows.Count -eq 0) {
        Write-Host 'No source candidates found under SearchRoots'
    } else {
        $sourceRows | Format-Table FileName,Length,LastWriteTime,SHA256,FullName -AutoSize
    }

    $jarRows | Export-Csv -LiteralPath $jarReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8
    $sourceRows | Export-Csv -LiteralPath $sourceReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

    @(
        'TRACE ACTIVE CLIENT PROVENANCE v1.0.0'
        "Finished: $(Get-Date -Format o)"
        "InstallRoot: $InstallRoot"
        "ActiveClientJar: $activeClientJar"
        "ActiveClientSHA256: $activeClientHash"
        "ActiveClientMageSetsSHA256: $activeSetsClientHash"
        "ActiveServerMageSetsSHA256: $activeServerSetsHash"
        "JAR report: $jarReport"
        "Source report: $sourceReport"
        'Read-only operation. No installation, source, or card image was modified.'
        'Interpretation: an exact SHA256 match identifies a binary copy of the active client JAR.'
    ) | Set-Content -LiteralPath $readme -Encoding UTF8

    Write-Host ''
    Write-Host 'RESULT: provenance scan completed'
    Write-Host "JAR REPORT: $jarReport"
    Write-Host "SOURCE REPORT: $sourceReport"
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
