@echo off
setlocal

echo ============================================================
echo  TAQANA Busbar Generator
echo ============================================================
echo.

:: ── Find python path saved by install.bat ────────────────────
if not exist busbar_python_path.txt (
  echo ERROR: busbar_python_path.txt not found.
  echo Please run install.bat first.
  echo.
  pause
  exit /b 1
)

set /p BUSBAR_PYTHON=<busbar_python_path.txt

:: Trim whitespace
set BUSBAR_PYTHON=%BUSBAR_PYTHON: =%

if not exist "%BUSBAR_PYTHON%" (
  echo ERROR: Python not found at: %BUSBAR_PYTHON%
  echo The busbar environment may have been moved or deleted.
  echo Please run install.bat again to repair.
  echo.
  pause
  exit /b 1
)

:: ── Verify CadQuery ──────────────────────────────────────────
"%BUSBAR_PYTHON%" -c "import cadquery" 2>nul
if %ERRORLEVEL% NEQ 0 (
  echo ERROR: CadQuery not found in the busbar environment.
  echo Please run install.bat again to repair.
  echo.
  pause
  exit /b 1
)

:: ── Start app ────────────────────────────────────────────────
echo Starting Busbar Generator...
echo Browser will open automatically.
echo.
echo To stop the server, close this window or press Ctrl+C.
echo.

cd /d "%~dp0"
"%BUSBAR_PYTHON%" app.py

pause
exit /b 0
