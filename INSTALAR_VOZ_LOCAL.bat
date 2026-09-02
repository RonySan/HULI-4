@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente Python da Huli nao encontrado.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -e ".[voice]"
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m tools.install_voice_model
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m tools.diagnose_voice
if errorlevel 1 goto failed
echo Configuracao pronta. Execute TESTAR_VOZ.bat para testar sua fala.
pause
exit /b 0
:failed
echo Instalacao ou diagnostico incompleto. Leia a mensagem acima.
pause
exit /b 1
