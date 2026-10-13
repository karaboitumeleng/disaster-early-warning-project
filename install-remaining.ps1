$ErrorActionPreference = "Stop"
$root = (Get-Location).Path
if (-not (Test-Path (Join-Path $root "backend/app/main.py"))) {
    throw "Run this from the disaster-early-warning folder (backend/app/main.py not found)."
}
$utf8 = New-Object System.Text.UTF8Encoding($false)
$script:patchFailures = @()

function Write-File([string]$Path, [string]$Content) {
    $full = Join-Path $root $Path
    New-Item -ItemType Directory -Force -Path (Split-Path $full -Parent) | Out-Null
    if ((Test-Path $full) -and -not (Test-Path "$full.bak")) { Copy-Item $full "$full.bak" }
    $text = ($Content -replace "`r`n", "`n")
    [IO.File]::WriteAllText($full, $text + "`n", $utf8)
    Write-Host "wrote  $Path"
}

function Append-File([string]$Path, [string]$Content) {
    $full = Join-Path $root $Path
    $existing = [IO.File]::ReadAllText($full)
    if ($existing.Contains("/* ---- v2 additions ---- */")) { Write-Host "skip   $Path (already appended)"; return }
    $text = ($Content -replace "`r`n", "`n")
    [IO.File]::WriteAllText($full, $existing + "`n" + $text + "`n", $utf8)
    Write-Host "append $Path"
}

function Patch-File([string]$Path, [string]$Old, [string]$New) {
    $full = Join-Path $root $Path
    $text = ([IO.File]::ReadAllText($full) -replace "`r`n", "`n")
    if ($text.Contains($New)) { Write-Host "patched already: $Path"; return }
    if (-not $text.Contains($Old)) {
        $script:patchFailures += "$Path : could not find: $Old"
        Write-Warning "Patch failed for $Path (apply manually, see summary)"
        return
    }
    [IO.File]::WriteAllText($full, $text.Replace($Old, $New), $utf8)
    Write-Host "patch  $Path"
}