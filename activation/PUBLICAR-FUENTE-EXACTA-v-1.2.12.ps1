param(
    [string]$SourceRoot = 'J:\mtg\_ARCHIVO\RC1.1-WORK-PILE-1.1\XMage-Stack-Floating-v-1.2.1.9.10.6.5-TEST\source\rc1.1-complete-community',
    [string]$ExportRoot = 'J:\mtg\_ARCHIVO\RC1.1-WORK-PILE-1.1\XMAGE-SOURCE-EXACT-v-1.2.12',
    [string]$LogRoot = 'J:\mtg\_LOGS'
)

$ErrorActionPreference = 'Stop'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$log = Join-Path $LogRoot "publicar-fuente-exacta-v-1.2.12-$stamp.log"
$files = @(
    'Mage.Client\src\main\java\mage\client\game\GamePanel.java',
    'Mage.Client\src\main\java\mage\client\cards\Cards.java',
    'Mage.Client\src\main\java\mage\client\plugins\adapters\MageActionCallback.java'
)

New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
Start-Transcript -Path $log -Force | Out-Null
try {
    if (-not (Test-Path -LiteralPath $SourceRoot -PathType Container)) { throw "No existe SourceRoot: $SourceRoot" }
    if ($SourceRoot -match 'J:\\mtg\\xmage|PRIVADO-BLINDADO|RC1\.1-COMPLETA-PORTABLE') { throw 'SourceRoot apunta a una ruta protegida' }
    if ($ExportRoot -match 'J:\\mtg\\xmage|PRIVADO-BLINDADO|RC1\.1-COMPLETA-PORTABLE') { throw 'ExportRoot apunta a una ruta protegida' }

    New-Item -ItemType Directory -Force -Path $ExportRoot | Out-Null
    $manifest = New-Object System.Collections.Generic.List[string]
    $manifest.Add('XMAGE exact final source publication manifest v-1.2.12')
    $manifest.Add("source=$SourceRoot")
    $manifest.Add("created=$stamp")
    foreach ($relative in $files) {
        $src = Join-Path $SourceRoot $relative
        if (-not (Test-Path -LiteralPath $src -PathType Leaf)) { throw "Falta fuente exacta: $src" }
        $dst = Join-Path $ExportRoot $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force
        $hash = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash
        $manifest.Add("$hash  $relative")
    }
    $manifestPath = Join-Path $ExportRoot 'SOURCE-MANIFEST-SHA256-v-1.2.12.txt'
    $manifest | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    Write-Host "OK: fuente exacta exportada y verificada: $ExportRoot"
    Write-Host "MANIFEST: $manifestPath"
    Write-Host "LOG: $log"
}
finally {
    Stop-Transcript | Out-Null
}

