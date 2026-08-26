$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host " HULI 4 - VALIDACAO DA FASE 2 / MEMORIA"
Write-Host "=========================================="

$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Ambiente virtual nao encontrado em .venv."
}

Push-Location (Join-Path $PSScriptRoot "..")
try {
    Write-Host "[1/6] Instalando dependencias..."
    & $python -m pip install -e ".[dev]"

    Write-Host "[2/6] Ruff..."
    & $python -m ruff check .

    Write-Host "[3/6] Pytest completo..."
    & $python -m pytest

    Write-Host "[4/6] Regressao da Fase 0..."
    & $python tools/validate_phase0.py

    Write-Host "[5/6] Regressao da Fase 1..."
    & $python tools/validate_phase1.py

    Write-Host "[6/6] Memory Engine 4.0..."
    & $python tools/validate_phase2.py

    Write-Host ""
    Write-Host "=========================================="
    Write-Host " FASE 2 APROVADA NESTE COMPUTADOR"
    Write-Host "=========================================="
}
finally {
    Pop-Location
}
