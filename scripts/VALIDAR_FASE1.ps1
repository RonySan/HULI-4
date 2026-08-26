$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host " HULI 4 - VALIDACAO FINAL DA FASE 1"
Write-Host "=========================================="

$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Ambiente virtual nao encontrado em .venv." }

Push-Location (Join-Path $PSScriptRoot "..")
try {
    & $python -m pip install -e ".[dev]"
    & $python -m ruff check .
    & $python -m pytest
    & $python tools/validate_phase0.py
    & $python tools/validate_intent_engine.py
    & $python tools/validate_phase1.py

    Write-Host ""
    Write-Host "=========================================="
    Write-Host " FASE 1 APROVADA NESTE COMPUTADOR"
    Write-Host "=========================================="
}
finally { Pop-Location }
