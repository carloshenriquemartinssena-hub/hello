@echo off
setlocal
cd /d "%~dp0"
echo Preparando ambiente Python EXCLUSIVO do CRM 2...
if exist ".venv\Scripts\python.exe" goto dependencies
py -3.12 -m venv .venv
if not errorlevel 1 goto dependencies
python -m venv .venv
if errorlevel 1 goto failed
:dependencies
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" iniciar.py --instalar-inicio
if errorlevel 1 goto failed
echo Instalacao do CRM 2 concluida. Confira data\automation.log.
pause
exit /b 0
:failed
echo Nao foi possivel concluir. Confira as mensagens acima, Python 3.12 e configuracao local.
echo Nenhum ambiente ou tarefa do CRM principal foi alterado.
pause
exit /b 1
