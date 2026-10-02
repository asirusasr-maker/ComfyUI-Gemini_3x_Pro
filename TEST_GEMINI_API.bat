@echo off
setlocal
set "HERE=%~dp0"
set "PY=%HERE%..\..\..\python_embeded\python.exe"
if not exist "%PY%" (
  echo ERROR: embedded Python not found.
  pause
  exit /b 1
)
"%PY%" "%HERE%test_gemini_api.py"
pause
