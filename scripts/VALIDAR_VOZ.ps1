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
    Write-Host "[1/4] Ruff..."
    & $python -m ruff check .
    if ($LASTEXITCODE -ne 0) { throw "Ruff falhou." }

    Write-Host "[2/4] Testes completos..."
    & $python -m pytest
    if ($LASTEXITCODE -ne 0) { throw "Testes falharam." }

    Write-Host "[3/4] Validacao logica da voz e agenda natural..."
    & $python tools/validate_voice.py
    if ($LASTEXITCODE -ne 0) { throw "Validacao logica falhou." }
    Write-Host "[4/4] Motores e microfone configurado..."
    & $python -m tools.diagnose_voice
    if ($LASTEXITCODE -ne 0) { throw "Configuracao real de voz incompleta." }

    Write-Host ""
    Write-Host "=========================================="
    Write-Host " TESTES E CONFIGURACAO DE VOZ VERIFICADOS"
    Write-Host " Execute TESTAR_VOZ.bat para confirmar fala e escuta reais."
    Write-Host "=========================================="
}
finally {
    Pop-Location
}
