@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set HULI_VOICE_INPUT_PROVIDER=auto
set HULI_VOICE_INPUT_TIMEOUT=20
set HULI_VOICE_WAKE_ENABLED=true
set HULI_VOICE_AUTO_SPEAK=true
set HULI_DESKTOP_RESIDENT_ENABLED=true
if not exist ".venv\Scripts\pythonw.exe" (
    echo Ambiente Python da Huli nao encontrado.
    echo Execute primeiro a instalacao do projeto.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" huli_preflight.py --voice --desktop
if errorlevel 1 (
    pause
    exit /b 1
)
start "Huli" ".venv\Scripts\pythonw.exe" painel.py --resident
endlocal
