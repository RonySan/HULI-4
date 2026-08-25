$ErrorActionPreference = 'Stop'

Write-Host ''
Write-Host '=========================================='
Write-Host ' HULI 4 - VALIDACAO FINAL DA FASE 0'
Write-Host '=========================================='
Write-Host ''

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    throw 'Ambiente .venv nao encontrado. Crie-o com: py -3.11 -m venv .venv'
}

$python = '.\.venv\Scripts\python.exe'

Write-Host '[1/5] Python...'
& $python --version

Write-Host '[2/5] Instalando/atualizando dependencias de desenvolvimento...'
& $python -m pip install -e '.[dev]'

Write-Host '[3/5] Ruff...'
& $python -m ruff check .

Write-Host '[4/5] Pytest...'
& $python -m pytest

Write-Host '[5/5] Fluxo automatizado da Fase 0...'
& $python tools\validate_phase0.py

Write-Host ''
Write-Host '=========================================='
Write-Host ' FASE 0 APROVADA NESTE COMPUTADOR'
Write-Host '=========================================='
Write-Host ''
Write-Host 'Ainda resta apenas o teste manual da interface local:'
Write-Host '  python main.py'
Write-Host 'Teste login, ping, fallback e sair.'
