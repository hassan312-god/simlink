# Simlink Local — installation en une commande (Windows PowerShell).
# Crée un environnement virtuel, installe le moteur puis lance la configuration.
# Usage : .\install.ps1 [-Kerbal]
param([switch]$Kerbal)
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot
$python = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { $null }
if (-not $python) { Write-Error 'Simlink : Python 3.10 ou plus est requis (https://www.python.org/downloads/).' }
& $python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
if ($LASTEXITCODE -ne 0) { Write-Error 'Simlink : Python 3.10 ou plus est requis.' }
if (-not (Test-Path .venv)) { & $python -m venv .venv }
$venv = '.\.venv\Scripts\python.exe'
$extra = if ($Kerbal) { '.[kerbal]' } else { '.' }
& $venv -m pip install --quiet --upgrade pip
& $venv -m pip install --quiet $extra
Write-Host "Moteur installé dans $PSScriptRoot\.venv"
$config = Join-Path $HOME '.simlink\config.json'
if (Test-Path $config) { Write-Host "Configuration existante conservée : $config" } else { & $venv -m simlink setup }
Write-Host ''
Write-Host 'Étapes suivantes :'
Write-Host '  .\.venv\Scripts\python.exe -m simlink doctor         # lecture réelle du jeu'
Write-Host '  .\.venv\Scripts\python.exe -m simlink dashboard      # panneau d’approbation local'
Write-Host '  .\.venv\Scripts\python.exe -m simlink client-config  # bloc à coller dans votre client MCP'
