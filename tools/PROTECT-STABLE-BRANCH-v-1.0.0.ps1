[CmdletBinding()]
param(
    [string]$Repository = 'vros01-Kabutosan/XMage-Community-Patch',
    [string]$Branch = 'port/1.4.61V1-community-patch',
    [string]$LogRoot = 'J:\mtg\_LOGS'
)

$ErrorActionPreference = 'Stop'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runName = "PROTECT-STABLE-BRANCH-v-1.0.0-$stamp"
$runDir = Join-Path $LogRoot $runName
$runLog = Join-Path $runDir 'RUN.log'
$resultReport = Join-Path $runDir 'RESULT.tsv'
$payloadPath = Join-Path $runDir 'RULESET.json'
$transcriptStarted = $false

function Invoke-GhApi {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $output = & gh @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub CLI failed ($LASTEXITCODE): $($output -join [Environment]::NewLine)"
    }

    return ($output -join [Environment]::NewLine)
}

try {
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
    Start-Transcript -LiteralPath $runLog -Force | Out-Null
    $transcriptStarted = $true

    $refName = "refs/heads/$Branch"

    Write-Host 'PROTECT STABLE BRANCH v1.0.0'
    Write-Host "Repository: $Repository"
    Write-Host "Stable branch: $Branch"
    Write-Host "Log: $runLog"
    Write-Host 'SAFETY: no source changes, no history rewrite, no deletes'

    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw 'GitHub CLI (gh) no está instalado o no está en PATH'
    }

    Invoke-GhApi -Arguments @('auth', 'status') | Out-Host

    $rulesetsJson = Invoke-GhApi -Arguments @(
        'api',
        '--method', 'GET',
        "repos/$Repository/rulesets"
    )
    $rulesets = @($rulesetsJson | ConvertFrom-Json)

    $existing = @($rulesets | Where-Object {
        $_.name -eq 'LOCK-STABLE-RC1.1' -and $_.target -eq 'branch'
    })

    if ($existing.Count -gt 1) {
        throw 'Hay varios rulesets LOCK-STABLE-RC1.1; se requiere revisión manual'
    }

    if ($existing.Count -eq 1) {
        $detailsJson = Invoke-GhApi -Arguments @(
            'api',
            '--method', 'GET',
            "repos/$Repository/rulesets/$($existing[0].id)"
        )
        $details = $detailsJson | ConvertFrom-Json
        $includes = @($details.conditions.ref_name.include)
        $ruleTypes = @($details.rules | ForEach-Object { $_.type })
        $pullRule = @($details.rules | Where-Object { $_.type -eq 'pull_request' }) | Select-Object -First 1
        $mergeMethods = @($pullRule.parameters.allowed_merge_methods)

        if (
            $details.enforcement -eq 'active' -and
            $includes -contains $refName -and
            $ruleTypes -contains 'deletion' -and
            $ruleTypes -contains 'non_fast_forward' -and
            $ruleTypes -contains 'pull_request' -and
            $mergeMethods -contains 'squash'
        ) {
            [PSCustomObject][ordered]@{
                Status = 'ALREADY_PROTECTED'
                Repository = $Repository
                Branch = $Branch
                RulesetId = $details.id
                Enforcement = $details.enforcement
                Rules = ($ruleTypes -join ',')
                SourceChanges = $false
                HistoryRewritten = $false
                DeletesPerformed = $false
            } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

            Write-Host "RESULT: ALREADY_PROTECTED (ruleset $($details.id))"
            Write-Host "RESULT REPORT: $resultReport"
            exit 0
        }

        throw "Existe LOCK-STABLE-RC1.1 pero no coincide exactamente con la política; no se modifica"
    }

    $payload = [ordered]@{
        name = 'LOCK-STABLE-RC1.1'
        target = 'branch'
        enforcement = 'active'
        conditions = [ordered]@{
            ref_name = [ordered]@{
                include = @($refName)
                exclude = @()
            }
        }
        rules = @(
            [ordered]@{ type = 'deletion' },
            [ordered]@{ type = 'non_fast_forward' },
            [ordered]@{
                type = 'pull_request'
                parameters = [ordered]@{
                    allowed_merge_methods = @('squash')
                    dismiss_stale_reviews_on_push = $true
                    require_code_owner_review = $false
                    require_last_push_approval = $false
                    required_approving_review_count = 1
                    required_review_thread_resolution = $true
                }
            }
        )
        bypass_actors = @()
    }

    $payloadJson = $payload | ConvertTo-Json -Depth 10
    # Windows PowerShell 5.1 writes a BOM with UTF8; GitHub's JSON parser rejects it.
    $payloadJson | Set-Content -LiteralPath $payloadPath -Encoding ASCII
    Write-Host "RULESET PAYLOAD: $payloadPath"

    $createdJson = Invoke-GhApi -Arguments @(
        'api',
        '--method', 'POST',
        "repos/$Repository/rulesets",
        '--input', $payloadPath
    )
    $created = $createdJson | ConvertFrom-Json

    if ($created.name -ne 'LOCK-STABLE-RC1.1' -or $created.enforcement -ne 'active') {
        throw 'GitHub no confirmó el ruleset activo'
    }

    $verifyJson = Invoke-GhApi -Arguments @(
        'api',
        '--method', 'GET',
        "repos/$Repository/rulesets/$($created.id)"
    )
    $verify = $verifyJson | ConvertFrom-Json
    $verifiedTypes = @($verify.rules | ForEach-Object { $_.type })
    $verifiedIncludes = @($verify.conditions.ref_name.include)
    $verifiedPullRule = @($verify.rules | Where-Object { $_.type -eq 'pull_request' }) | Select-Object -First 1
    $verifiedMergeMethods = @($verifiedPullRule.parameters.allowed_merge_methods)

    if (
        $verify.enforcement -ne 'active' -or
        $verifiedIncludes -notcontains $refName -or
        $verifiedTypes -notcontains 'deletion' -or
        $verifiedTypes -notcontains 'non_fast_forward' -or
        $verifiedTypes -notcontains 'pull_request' -or
        $verifiedMergeMethods -notcontains 'squash'
    ) {
        throw 'La verificación posterior no coincide con la política solicitada'
    }

    [PSCustomObject][ordered]@{
        Status = 'PROTECTED'
        Repository = $Repository
        Branch = $Branch
        RulesetId = $verify.id
        Enforcement = $verify.enforcement
        Rules = ($verifiedTypes -join ',')
        RequiredApprovals = 1
        SourceChanges = $false
        HistoryRewritten = $false
        DeletesPerformed = $false
    } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8

    Write-Host "RESULT: PROTECTED (ruleset $($verify.id))"
    Write-Host "RESULT REPORT: $resultReport"
}
catch {
    Write-Host "ABORTED: $($_.Exception.Message)"
    try {
        [PSCustomObject][ordered]@{
            Status = 'ABORTED'
            Error = $_.Exception.Message
            Repository = $Repository
            Branch = $Branch
            SourceChanges = $false
            HistoryRewritten = $false
            DeletesPerformed = $false
        } | Export-Csv -LiteralPath $resultReport -Delimiter ([char]9) -NoTypeInformation -Encoding UTF8
    }
    catch {
        Write-Host "REPORT ERROR: $($_.Exception.Message)"
    }
    exit 1
}
finally {
    if ($transcriptStarted) {
        Stop-Transcript | Out-Null
    }
}
