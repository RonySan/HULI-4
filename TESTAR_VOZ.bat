@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set HULI_VOICE_INPUT_PROVIDER=vosk
".venv\Scripts\python.exe" -m tools.diagnose_voice --speak --listen
if errorlevel 1 echo O teste nao foi aprovado. Confira a mensagem acima.
pause
endlocal
