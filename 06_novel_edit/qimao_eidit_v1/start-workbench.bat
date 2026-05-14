@echo off
setlocal EnableExtensions
rem Pure ASCII: CMD uses OEM/GBK by default; UTF-8 Chinese breaks parsing.
set "ROOT=%~dp0"
cd /d "%ROOT%" || (
  echo ERROR: cannot cd to "%ROOT%"
  pause
  exit /b 1
)
set "PY_EXE=%ROOT%.venv\Scripts\python.exe"
set "LAUNCH=%ROOT%launch_desktop.py"
if not exist "%PY_EXE%" (
  echo ERROR: "%PY_EXE%" not found.
  echo Create venv:  python -m venv .venv
  echo Install deps: .venv\Scripts\pip install -r requirements.txt -r requirements-desktop.txt
  pause
  exit /b 1
)
if not exist "%LAUNCH%" (
  echo ERROR: "%LAUNCH%" not found.
  pause
  exit /b 1
)
"%PY_EXE%" "%LAUNCH%"
if errorlevel 1 pause
