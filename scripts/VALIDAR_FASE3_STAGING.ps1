$ErrorActionPreference = "Stop"

Write-Host "=================================================="
Write-Host " HULI 4 - VALIDACAO DA FASE 3 / KNOWLEDGE STAGING"
Write-Host "=================================================="

$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Ambiente virtual nao encontrado em .venv."
}

Push-Location (Join-Path $PSScriptRoot "..")
try {
    Write-Host "[1/7] Instalando dependencias..."
    & $python -m pip install -e ".[dev]"

    Write-Host "[2/7] Ruff..."
    & $python -m ruff check .

    Write-Host "[3/7] Pytest completo..."
    & $python -m pytest

    Write-Host "[4/7] Regressao da Fase 0..."
    & $python tools/validate_phase0.py

    Write-Host "[5/7] Regressao da Fase 1..."
    & $python tools/validate_phase1.py

    Write-Host "[6/7] Regressao da Fase 2..."
    & $python tools/validate_phase2.py

    Write-Host "[7/7] Personal Knowledge Graph staging..."
    & $python tools/validate_phase3_staging.py

    Write-Host ""
    Write-Host "=================================================="
    Write-Host " FASE 3 STAGING APROVADA NESTE COMPUTADOR"
    Write-Host "=================================================="
}
finally {
    Pop-Location
}
