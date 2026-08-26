[CmdletBinding()]
param(
    [string]$InstallRoot = 'J:\mtg\xmage',
    [string]$SourceZip = '',
    [string]$LogRoot = 'J:\mtg\_LOGS'
)

$ErrorActionPreference = 'Stop'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logPath = Join-Path $LogRoot "AUDIT-CURRENT-XMAGE-INSTALL-$stamp.log"
New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null

function Write-Log([string]$line) {
    $line | Tee-Object -FilePath $logPath -Append
}

Write-Log "XMage current installation audit"
Write-Log "Started: $(Get-Date -Format o)"
Write-Log "InstallRoot: $InstallRoot"
Write-Log "SourceZip: $SourceZip"
Write-Log "READ-ONLY AUDIT: no installation files are changed."

if (-not (Test-Path -LiteralPath $InstallRoot -PathType Container)) {
    throw "Installation path not found: $InstallRoot"
}

Write-Log "`n[INSTALL FILE INVENTORY: SHA256]"
Get-ChildItem -LiteralPath $InstallRoot -File -Recurse -Force |
    Sort-Object FullName |
    ForEach-Object {
        $relative = $_.FullName.Substring($InstallRoot.Length).TrimStart('\')
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        Write-Log ("{0}`t{1}`t{2}`t{3}" -f $relative, $_.Length, $_.LastWriteTimeUtc.ToString('o'), $hash)
    }

if ($SourceZip -and (Test-Path -LiteralPath $SourceZip -PathType Leaf)) {
    Write-Log "`n[SOURCE ZIP]"
    $zipHash = (Get-FileHash -LiteralPath $SourceZip -Algorithm SHA256).Hash
    $zipItem = Get-Item -LiteralPath $SourceZip
    Write-Log ("{0}`t{1}`t{2}" -f $zipItem.Length, $zipItem.LastWriteTimeUtc.ToString('o'), $zipHash)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($SourceZip)
    try {
        Write-Log ("ZIP_ENTRIES`t{0}" -f $archive.Entries.Count)
        $archive.Entries | Sort-Object FullName | ForEach-Object {
            Write-Log ("{0}`t{1}" -f $_.FullName, $_.Length)
        }
    } finally {
        $archive.Dispose()
    }
}

Write-Log "`n[END]"
Write-Log "Finished: $(Get-Date -Format o)"
Write-Log "Log: $logPath"
Write-Output $logPath
