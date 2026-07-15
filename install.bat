@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo  TAQANA Busbar Generator — Installation
echo ============================================================
echo.
echo This will set up the busbar Python environment.
echo It requires an internet connection and takes ~15 minutes.
echo.

:: ── Step 1: Find conda ──────────────────────────────────────
echo [1/4] Looking for conda...

set CONDA_EXE=
for %%P in (
  "%USERPROFILE%\miniconda3\Scripts\conda.exe"
  "%USERPROFILE%\anaconda3\Scripts\conda.exe"
  "%LOCALAPPDATA%\miniconda3\Scripts\conda.exe"
  "%LOCALAPPDATA%\Continuum\miniconda3\Scripts\conda.exe"
  "C:\miniconda3\Scripts\conda.exe"
  "C:\anaconda3\Scripts\conda.exe"
) do (
  if exist %%P (
    set CONDA_EXE=%%P
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
echo During install, check "Add Miniconda to PATH" if asked.
echo Then run install.bat again.
echo.
pause
exit /b 1

:found_conda
echo     Found conda at: %CONDA_EXE%
echo.

:: ── Step 2: Check if busbar env already exists ───────────────
echo [2/4] Checking for existing busbar environment...

"%CONDA_EXE%" env list 2>nul | findstr /C:"busbar" >nul
if %ERRORLEVEL% EQU 0 (
  echo     Environment 'busbar' already exists.
  echo     Skipping creation. If you want to reinstall, run:
  echo       conda env remove -n busbar
  echo     Then run install.bat again.
  goto :verify
)

:: ── Step 3: Create environment ───────────────────────────────
echo [3/4] Creating busbar environment with Python 3.10 + CadQuery...
echo     This will take 10-20 minutes on first run.
echo.

"%CONDA_EXE%" create -n busbar python=3.10 cadquery=2.8 -c conda-forge -c defaults --ssl-verify false -y

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo ERROR: Environment creation failed.
  echo Check your internet connection and try again.
  echo If you are on a corporate network, you may need to
  echo contact your IT department about SSL certificate issues.
  echo.
  pause
  exit /b 1
)

:: ── Step 4: Install FastAPI + uvicorn ────────────────────────
echo.
echo [4/4] Installing FastAPI and uvicorn...

:: Find the busbar env python
set BUSBAR_PYTHON=
for %%P in (
  "%USERPROFILE%\miniconda3\envs\busbar\python.exe"
  "%USERPROFILE%\anaconda3\envs\busbar\python.exe"
  "%LOCALAPPDATA%\miniconda3\envs\busbar\python.exe"
  "C:\miniconda3\envs\busbar\python.exe"
  "C:\anaconda3\envs\busbar\python.exe"
) do (
  if exist %%P (
    set BUSBAR_PYTHON=%%P
    goto :found_python
  )
)

echo ERROR: Could not find busbar env python.exe after creation.
echo Please report this error.
pause
exit /b 1

:found_python
echo     Found busbar Python at: %BUSBAR_PYTHON%

"%BUSBAR_PYTHON%" -m pip install fastapi uvicorn[standard] --quiet

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo ERROR: pip install failed.
  echo.
  pause
  exit /b 1
)

:: ── Save python path for run.bat ─────────────────────────────
echo %BUSBAR_PYTHON% > busbar_python_path.txt
echo     Saved Python path to busbar_python_path.txt

goto :done

:verify
:: Env existed — find python and save path
echo     Verifying existing environment...
set BUSBAR_PYTHON=
for %%P in (
  "%USERPROFILE%\miniconda3\envs\busbar\python.exe"
  "%USERPROFILE%\anaconda3\envs\busbar\python.exe"
  "%LOCALAPPDATA%\miniconda3\envs\busbar\python.exe"
  "C:\miniconda3\envs\busbar\python.exe"
  "C:\anaconda3\envs\busbar\python.exe"
) do (
  if exist %%P (
    set BUSBAR_PYTHON=%%P
    goto :verify_pip
  )
)
echo ERROR: Could not find busbar python.exe. Try removing and recreating:
echo   conda env remove -n busbar
pause
exit /b 1

:verify_pip
"%BUSBAR_PYTHON%" -m pip install fastapi uvicorn[standard] --quiet
echo %BUSBAR_PYTHON% > busbar_python_path.txt

:done
echo.
echo ============================================================
echo  Installation complete!
echo ============================================================
echo.
echo To start the app, double-click run.bat
echo.
pause
exit /b 0
