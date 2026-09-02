param(
    [string]$Time = "05:50",
    [string]$AudioPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($Time -notmatch '^(?:[01]\d|2[0-3]):[0-5]\d$') {
    throw "Horário inválido. Use HH:mm, por exemplo 05:50."
}

$appRoot = Split-Path -Parent $PSScriptRoot
$alarmScript = Join-Path $appRoot "tools\morning_alarm.py"
$pythonw = Join-Path $appRoot ".venv\Scripts\pythonw.exe"
if (-not (Test-Path -LiteralPath $pythonw)) {
    $pythonwCommand = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($null -eq $pythonwCommand) {
        throw "Python sem janela não encontrado. Execute INSTALAR.bat primeiro."
    }
    $pythonw = $pythonwCommand.Source
}

if ($AudioPath) {
    $AudioPath = [IO.Path]::GetFullPath($AudioPath)
    if (-not (Test-Path -LiteralPath $AudioPath -PathType Leaf)) {
        throw "O arquivo de música não existe: $AudioPath"
    }
    if ([IO.Path]::GetExtension($AudioPath) -ne ".wav") {
        throw "Por segurança e reprodução local, use uma música em formato WAV."
    }
}

$dataDir = Join-Path $appRoot "data"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
$configPath = Join-Path $dataDir "morning_alarm.json"
$config = [ordered]@{
    time = $Time
    audio_path = $AudioPath
    snooze_minutes = 10
}
$config | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8

$hour, $minute = $Time.Split(':')
$triggerAt = [datetime]::Today.AddHours([int]$hour).AddMinutes([int]$minute)
$action = New-ScheduledTaskAction `
    -Execute $pythonw `
    -Argument ('"{0}"' -f $alarmScript) `
    -WorkingDirectory $appRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $triggerAt
$settings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal `
    -UserId $currentUser `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName "Huli Despertador Matinal" `
    -Description "Despertador diário da Huli com acesso ao painel pessoal." `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Host "Despertador da Huli configurado todos os dias às $Time."
Write-Host "O computador precisa estar ligado ou em suspensão com temporizadores de ativação permitidos."
if ($AudioPath) {
    Write-Host "Música: $AudioPath"
} else {
    Write-Host "Som: melodia local gratuita da Huli."
}
