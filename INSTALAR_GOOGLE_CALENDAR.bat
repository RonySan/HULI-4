@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente Python da Huli nao encontrado.
    pause
    exit /b 1
)
echo Instalando a integracao local do Google Calendar...
".venv\Scripts\python.exe" -m pip install -e ".[google-calendar]"
if errorlevel 1 goto failed
echo Pronto. Siga o guia em docs\GOOGLE_CALENDAR.md para criar sua credencial OAuth.
pause
exit /b 0
:failed
echo Nao foi possivel instalar a integracao.
pause
exit /b 1
