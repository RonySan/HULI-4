@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
".venv\Scripts\python.exe" -m tools.configure_windows_startup enable
if errorlevel 1 pause
endlocal
