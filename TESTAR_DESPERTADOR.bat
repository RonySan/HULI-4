@echo off
setlocal
cd /d "%~dp0"
set "PYTHONW=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%PYTHONW%" set "PYTHONW=pythonw.exe"
start "Huli Despertador" "%PYTHONW%" "%~dp0tools\morning_alarm.py"
