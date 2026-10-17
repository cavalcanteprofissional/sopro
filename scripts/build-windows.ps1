# build/build-windows.ps1 — gera o executável portátil do Sopro (docs/09).
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File build/build-windows.ps1
#   powershell -ExecutionPolicy Bypass -File build/build-windows.ps1 -Version 0.1.0 -SkipTests
#   powershell -ExecutionPolicy Bypass -File build/build-windows.ps1 -Python C:\Python312\python.exe
param(
    [string]$Version = "",
    [string]$Python = "",
    [switch]$SkipTests
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $Python) {
    $venvPy = Join-Path $root ".venv/Scripts/python.exe"
    if (Test-Path $venvPy) { $Python = $venvPy } else { $Python = "python" }
}

function Invoke-Step {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Comando falhou ($LASTEXITCODE): $Exe $($Arguments -join ' ')"
    }
}

if (-not $Version) {
    $raw = Get-Content pyproject.toml -Raw
    if ($raw -match 'version\s*=\s*"([^"]+)"') { $Version = $Matches[1] } else { $Version = "0.0.0" }
}

& $Python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller ausente em '$Python'. Instale com: $Python -m pip install -e `".[packaging]`""
}

if (-not $SkipTests) {
    Invoke-Step $Python @("-m", "pytest", "-q")
}

Invoke-Step $Python @("-m", "PyInstaller", "--noconfirm", "--clean", "sopro.spec")

if (-not (Test-Path "dist/Sopro/Sopro.exe")) {
    throw "Build nao gerou dist/Sopro/Sopro.exe"
}

$zip = "dist/Sopro-$Version-portable.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path "dist/Sopro" -DestinationPath $zip -Force

Get-ChildItem $zip |
    ForEach-Object {
        "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(), $_.Name
    } |
    Out-File "dist/SHA256SUMS.txt" -Encoding ascii

Write-Host ""
Write-Host "Build concluido: $zip"
Get-Content dist/SHA256SUMS.txt
