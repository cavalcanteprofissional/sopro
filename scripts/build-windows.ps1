# scripts/build-windows.ps1 — gera portátil (zip) e instalador (Inno Setup) do Sopro.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1 -Version 0.1.1 -SkipTests
#   powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1 -Python C:\Python312\python.exe
#   powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1 -SkipInstaller
#   powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1 -Iscc "C:\...\ISCC.exe"
param(
    [string]$Version = "",
    [string]$Python = "",
    [string]$Iscc = "",
    [switch]$SkipTests,
    [switch]$SkipInstaller
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

function Find-Iscc {
    param([string]$Explicit)
    if ($Explicit) {
        if (Test-Path $Explicit) { return (Resolve-Path $Explicit).Path }
        throw "ISCC.exe não encontrado no caminho informado: $Explicit"
    }
    $command = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $candidates = @()
    foreach ($base in @($env:LOCALAPPDATA, ${env:ProgramFiles(x86)}, $env:ProgramFiles)) {
        if ($base) {
            $candidates += (Join-Path $base "Programs\Inno Setup 6\ISCC.exe")
            $candidates += (Join-Path $base "Inno Setup 6\ISCC.exe")
        }
    }
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return (Resolve-Path $candidate).Path }
    }
    return $null
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

$assets = @($zip)
$setup = "dist/Sopro-Setup-$Version.exe"
if (-not $SkipInstaller) {
    $isccPath = Find-Iscc $Iscc
    if (-not $isccPath) {
        throw "Inno Setup (ISCC.exe) não encontrado. Instale o Inno Setup 6 ou use -Iscc <caminho> (ou -SkipInstaller)."
    }
    if (Test-Path $setup) { Remove-Item $setup -Force }
    Invoke-Step $isccPath @("/DVersion=$Version", "installer.iss")
    if (-not (Test-Path $setup)) {
        throw "Inno Setup não gerou $setup"
    }
    $assets += $setup
}

$assets |
    ForEach-Object {
        "{0}  {1}" -f (Get-FileHash $_ -Algorithm SHA256).Hash.ToLower(), (Split-Path $_ -Leaf)
    } |
    Out-File "dist/SHA256SUMS.txt" -Encoding ascii

Write-Host ""
Write-Host "Build concluido: $zip"
if (-not $SkipInstaller) { Write-Host "Instalador: $setup" }
Get-Content dist/SHA256SUMS.txt
