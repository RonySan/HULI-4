@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -m tools.google_calendar connect-write
pause
