$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host " HULI 4 - VALIDACAO DA FASE 4.1"
Write-Host " DIARIO PESSOAL PRIVADO"
Write-Host "=========================================="

$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Ambiente virtual nao encontrado em .venv."
}

Push-Location (Join-Path $PSScriptRoot "..")
try {
    Write-Host "[1/8] Instalando dependencias..."
    & $python -m pip install -e ".[dev]"

    Write-Host "[2/8] Ruff..."
    & $python -m ruff check .

    Write-Host "[3/8] Pytest completo..."
    & $python -m pytest

    Write-Host "[4/8] Regressao da Fase 0..."
    & $python tools/validate_phase0.py

    Write-Host "[5/8] Regressao das Fases 1 e 2..."
    & $python tools/validate_phase1.py
    & $python tools/validate_phase2.py

    Write-Host "[6/8] Regressao da Fase 3..."
    & $python tools/validate_phase3_staging.py

    Write-Host "[7/8] Regressao da Fase 4..."
    & $python tools/validate_phase4.py

    Write-Host "[8/8] Diario pessoal privado..."
    & $python tools/validate_phase4_journal.py

    Write-Host ""
    Write-Host "=========================================="
    Write-Host " FASE 4.1 APROVADA NESTE COMPUTADOR"
    Write-Host "=========================================="
}
finally {
    Pop-Location
}
