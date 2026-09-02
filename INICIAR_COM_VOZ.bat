@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set HULI_VOICE_AUTO_SPEAK=true
set HULI_VOICE_START_LISTENING=false
set HULI_VOICE_WAKE_ENABLED=true
set HULI_VOICE_WAKE_CYCLE_TIMEOUT=30
set HULI_VOICE_INPUT_PROVIDER=vosk
set HULI_VOICE_INPUT_TIMEOUT=20
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente Python da Huli nao encontrado.
    pause
    exit /b 1
)
echo Huli local: ativacao por "Huli" e teclado ao mesmo tempo apos seu login.
echo Digite normalmente; use "pausar ativacao" para desligar o microfone.
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
endlocal
