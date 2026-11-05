@echo off
setlocal
cd /d "%~dp0.."
if not exist "frontend\.venv\Scripts\python.exe" (
  py -m venv "frontend\.venv"
  if errorlevel 1 goto :error
)
"frontend\.venv\Scripts\python.exe" -m pip install -r "frontend\requirements_frontend.txt"
if errorlevel 1 goto :error
"frontend\.venv\Scripts\python.exe" -m streamlit run app.py
pause
exit /b 0
:error
echo [ERROR] Check Python installation or internet connection.
pause
exit /b 1
