$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host " HULI 4 - VALIDACAO DO CEREBRO BASICO"
Write-Host "=========================================="

$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Ambiente virtual nao encontrado em .venv."
}

Push-Location (Join-Path $PSScriptRoot "..")
try {
    & $python -m pip install -e ".[dev]"
    & $python -m ruff check .
    & $python -m pytest tests/test_intent.py tests/test_intent_events.py tests/test_brain_dispatcher.py tests/test_bootstrap.py tests/test_auth.py
    & $python tools/validate_intent_engine.py

    Write-Host ""
    Write-Host "=========================================="
    Write-Host " INTENT + DISPATCHER APROVADOS NESTE PC"
    Write-Host "=========================================="
}
finally {
    Pop-Location
}
