@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente Python da Huli nao encontrado.
    pause
    exit /b 1
)
echo Instalando o reconhecimento Whisper local. Nao existe cobranca por uso.
".venv\Scripts\python.exe" -m pip install -e ".[voice,voice-whisper,desktop]"
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m tools.install_whisper_model
if errorlevel 1 goto failed
set HULI_VOICE_INPUT_PROVIDER=whisper
".venv\Scripts\python.exe" -m tools.diagnose_voice
if errorlevel 1 goto failed
echo Voz melhorada pronta. Feche e abra novamente o painel da Huli.
pause
exit /b 0
:failed
echo Nao foi possivel concluir. O Vosk anterior continua disponivel.
pause
exit /b 1
