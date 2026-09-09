@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente Python da Huli nao encontrado.
    pause
    exit /b 1
)
echo Instalando o icone da Huli na bandeja do Windows...
".venv\Scripts\python.exe" -m pip install -e ".[desktop]"
if errorlevel 1 goto failed
".venv\Scripts\python.exe" huli_preflight.py --desktop
if errorlevel 1 goto failed
echo Modo residente instalado. Abra a Huli com INICIAR_PAINEL.bat.
pause
exit /b 0
:failed
echo Nao foi possivel instalar o modo residente.
pause
exit /b 1
