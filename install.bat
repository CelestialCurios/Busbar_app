@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo  TAQANA Busbar Generator -- Installation
echo ============================================================
echo.
echo This will set up the busbar Python environment.
echo It requires an internet connection and takes ~15 minutes.
echo.

:: ── Step 1: Find conda root directory ───────────────────────
echo [1/4] Looking for conda...

set CONDA_ROOT=
for %%P in (
  "%USERPROFILE%\miniconda3"
  "%USERPROFILE%\anaconda3"
  "%USERPROFILE%\AppData\Local\miniconda3"
  "%USERPROFILE%\AppData\Local\anaconda3"
  "%USERPROFILE%\AppData\Local\Continuum\miniconda3"
  "%LOCALAPPDATA%\miniconda3"
  "%LOCALAPPDATA%\anaconda3"
  "C:\miniconda3"
  "C:\anaconda3"
  "C:\ProgramData\miniconda3"
  "C:\ProgramData\anaconda3"
) do (
  if exist "%%~P\Scripts\conda.exe" (
    set CONDA_ROOT=%%~P
    goto :found_conda
  )
)

:not_found
echo.
echo ERROR: conda not found on this machine.
echo.
echo Please install Miniconda first:
echo   https://docs.conda.io/en/latest/miniconda.html
echo.
echo Choose the Windows 64-bit installer.
echo Use all default settings during installation.
echo Then run install.bat again.
echo.
pause
exit /b 1

:found_conda
echo     Found conda at: %CONDA_ROOT%
echo.

:: Set conda exe path (no extra quotes — CONDA_ROOT already has none)
set CONDA_EXE=%CONDA_ROOT%\Scripts\conda.exe

:: ── Step 2: Check if busbar env already exists ───────────────
echo [2/4] Checking for existing busbar environment...

if exist "%CONDA_ROOT%\envs\busbar\python.exe" (
  echo     Environment 'busbar' already exists.
  echo     Skipping creation.
  set BUSBAR_PYTHON=%CONDA_ROOT%\envs\busbar\python.exe
  goto :install_pip
)

:: ── Step 3: Create environment ───────────────────────────────
echo [3/4] Creating busbar environment with Python 3.11 + CadQuery...
echo     This will take 10-20 minutes on first run.
echo.

call "%CONDA_EXE%" create -n busbar -c conda-forge python=3.11 cadquery --ssl-verify false -y

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo     First attempt failed. Trying without ssl-verify flag...
  echo.
  call "%CONDA_EXE%" create -n busbar -c conda-forge python=3.11 cadquery -y
)

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo ERROR: Environment creation failed.
  echo.
  echo Please try running this manually in Anaconda Prompt:
  echo   conda create -n busbar -c conda-forge python=3.11 cadquery
  echo.
  echo If that also fails, check your internet connection and try again.
  echo.
  pause
  exit /b 1
)

:: ── Step 4: Install FastAPI + uvicorn ────────────────────────
:install_pip
echo.
echo [4/4] Installing FastAPI and uvicorn...

set BUSBAR_PYTHON=%CONDA_ROOT%\envs\busbar\python.exe

if not exist "%BUSBAR_PYTHON%" (
  echo ERROR: Could not find python.exe in busbar environment.
  echo Expected at: %BUSBAR_PYTHON%
  echo.
  echo Please run this manually in Anaconda Prompt:
  echo   conda activate busbar
  echo   pip install fastapi "uvicorn[standard]"
  echo.
  pause
  exit /b 1
)

"%BUSBAR_PYTHON%" -m pip install fastapi "uvicorn[standard]" --quiet

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo ERROR: pip install failed.
  echo.
  echo Please run this manually in Anaconda Prompt:
  echo   conda activate busbar
  echo   pip install fastapi "uvicorn[standard]"
  echo.
  pause
  exit /b 1
)

:: ── Save python path ─────────────────────────────────────────
echo %BUSBAR_PYTHON%> busbar_python_path.txt
echo     Saved Python path to busbar_python_path.txt

:: ── Verify CadQuery ──────────────────────────────────────────
"%BUSBAR_PYTHON%" -c "import cadquery; print('CadQuery', cadquery.__version__, 'ready')"

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo WARNING: CadQuery import check failed.
  echo The environment may be incomplete. Try running install.bat again.
  echo.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  Installation complete!
echo ============================================================
echo.
echo To start the app, double-click run.bat
echo.
pause
exit /b 0
