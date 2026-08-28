$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host " HULI 4 - VALIDACAO DA VOZ LOCAL"
Write-Host "=========================================="

$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Ambiente virtual nao encontrado em .venv."
}

Push-Location (Join-Path $PSScriptRoot "..")
try {
    Write-Host "[1/4] Instalando dependencias..."
    & $python -m pip install -e ".[dev]"

    Write-Host "[2/4] Ruff..."
    & $python -m ruff check .

    Write-Host "[3/4] Testes completos..."
    & $python -m pytest

    Write-Host "[4/4] Validacao da voz e agenda natural..."
    & $python tools/validate_voice.py

    Write-Host ""
    Write-Host "=========================================="
    Write-Host " VOZ LOCAL APROVADA NESTE COMPUTADOR"
    Write-Host "=========================================="
}
finally {
    Pop-Location
}
