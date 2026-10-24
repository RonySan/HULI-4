@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set HULI_API_HOST=127.0.0.1
set HULI_API_PORT=8765
set HULI_REMOTE_ACCESS_ENABLED=true
if not exist ".venv\Scripts\python.exe" (
  echo [HULI] Ambiente Python ausente. Instale as dependencias conforme docs\MULTIDISPOSITIVO_ALPHA15.md.
  pause
  exit /b 1
)
echo =================================================
echo  HULI WEB 4.0.0-alpha.18
echo  Computador local: http://127.0.0.1:8765/app
echo  Acesso externo: somente via Tailscale Serve
echo  ATENCAO: senha forte de proprietario obrigatoria.
echo  Spotify: exige HULI_SPOTIFY_CLIENT_ID no ambiente.
echo =================================================
".venv\Scripts\python.exe" -m huli.api
set STATUS=%ERRORLEVEL%
if not "%STATUS%"=="0" pause
exit /b %STATUS%
