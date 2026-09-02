@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set HULI_VOICE_INPUT_PROVIDER=vosk
set HULI_VOICE_INPUT_TIMEOUT=20
if not exist ".venv\Scripts\pythonw.exe" (
    echo Ambiente Python da Huli nao encontrado.
    echo Execute primeiro a instalacao do projeto.
    pause
    exit /b 1
)
start "Huli" ".venv\Scripts\pythonw.exe" painel.py
endlocal
