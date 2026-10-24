# Testa alpha.15-18 em worktrees temporários; não altera o banco de dados existente.
# powershell -ExecutionPolicy Bypass -File .\scripts\VALIDAR_BRANCHES.ps1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$repo = [string](Resolve-Path (Join-Path $PSScriptRoot ".."))
$python = Join-Path $repo ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    throw "Python não localizado em $python. Crie .venv com Python 3.11."
}
$branches = @(
    "phase-6-multidevice-alpha15",
    "phase-7-ollama-alpha16",
    "phase-8-spotify-alpha17",
    "phase-9-devices-alpha18"
)
$root = Join-Path $env:TEMP ("huli-validacao-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $root -Force | Out-Null
Write-Host ""
Write-Host "H.U.L.I. - testes isolados" -ForegroundColor Cyan
Write-Host "Pasta temporária: $root"
Write-Host "Seu banco SQLite e sua branch atual não serão modificados."
$results = @()
try {
    git -C $repo fetch origin
    if ($LASTEXITCODE -ne 0) { throw "Falha ao obter branches do GitHub." }
    foreach ($branch in $branches) {
        $checkout = Join-Path $root $branch
        Write-Host ""
        Write-Host "Testando $branch" -ForegroundColor Cyan
        git -C $repo worktree add --detach $checkout "origin/$branch"
        if ($LASTEXITCODE -ne 0) {
            $results += [pscustomobject]@{ Branch = $branch; Ruff = "erro checkout"; Pytest = "não executado" }
            continue
        }
        try {
            Push-Location $checkout
            try {
                & $python -m ruff check .
                $ruffCode = $LASTEXITCODE
                & $python -m pytest -q
                $pytestCode = $LASTEXITCODE
                $results += [pscustomobject]@{
                    Branch = $branch
                    Ruff = $(if ($ruffCode -eq 0) { "OK" } else { "FALHOU ($ruffCode)" })
                    Pytest = $(if ($pytestCode -eq 0) { "OK" } else { "FALHOU ($pytestCode)" })
                }
            } finally {
                Pop-Location
            }
        } finally {
            git -C $repo worktree remove --force $checkout
            if ($LASTEXITCODE -ne 0) { Write-Warning "Não consegui remover o worktree $checkout." }
        }
    }
} finally {
    Write-Host ""
    Write-Host "=== RESULTADOS ===" -ForegroundColor Yellow
    $results | Format-Table -AutoSize
    if (Test-Path $root) {
        try { Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction Stop }
        catch { Write-Warning "Pasta temporária permanece em $root." }
    }
}
$failures = @($results | Where-Object { $_.Ruff -ne "OK" -or $_.Pytest -ne "OK" })
if ($results.Count -ne $branches.Count -or $failures.Count -gt 0) { exit 1 }
Write-Host "Todas as branches passaram." -ForegroundColor Green
