@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente Python da Huli nao encontrado.
    echo Reinstale o ambiente do projeto antes de continuar.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" huli_preflight.py --voice
echo.
if errorlevel 1 (
    echo A verificacao encontrou itens que precisam de reparo.
) else (
    echo Huli pronta para iniciar.
)
pause
endlocal
