@echo off
setlocal EnableExtensions

echo ============================================================
echo ComfyUI-Gemini_3x_Pro v2.0 - dependency installer
echo ============================================================

set "HERE=%~dp0"
set "PY=%HERE%..\..\..\python_embeded\python.exe"
set "REQ=%HERE%requirements.txt"

if not exist "%PY%" (
  echo ERROR: Could not find ComfyUI portable embedded Python.
  echo Expected: %PY%
  echo Run the command manually from your ComfyUI portable root:
  echo   python_embeded\python.exe -m pip install -r ComfyUI\custom_nodes\ComfyUI-Gemini_3x_Pro\requirements.txt
  pause
  exit /b 1
)

echo Using: %PY%
"%PY%" -m pip install -r "%REQ%"
if errorlevel 1 (
  echo.
  echo ERROR: Dependency installation failed.
  pause
  exit /b 1
)

echo.
echo Dependencies installed successfully.
echo Your API key is NOT included in this package.
echo Put it in config.json or set GEMINI_API_KEY in the environment.
echo Restart ComfyUI after installation.
pause
