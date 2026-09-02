@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\install_morning_alarm.ps1" -Time "05:50" %*
if errorlevel 1 (
    echo.
    echo Nao foi possivel configurar o despertador.
    pause
    exit /b 1
)
echo.
echo Configuracao concluida.
pause
