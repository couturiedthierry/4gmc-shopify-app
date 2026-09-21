@echo off
setlocal
cd /d "%~dp0"

py -3.11 -c "import fastapi, uvicorn, httpx, cryptography" >nul 2>nul
if not errorlevel 1 set "GMC_PYTHON=py -3.11"

if not defined GMC_PYTHON if exist ".venv\Scripts\python.exe" set "GMC_PYTHON=.venv\Scripts\python.exe"
if not defined GMC_PYTHON (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "GMC_PYTHON=py -3"
    ) else (
        where python >nul 2>nul
        if errorlevel 1 (
            echo Python 3.11 or newer is required. Install Python, then run this launcher again.
            if "%~1"=="" pause
            exit /b 1
        )
        set "GMC_PYTHON=python"
    )
)

%GMC_PYTHON% -c "import fastapi, uvicorn, httpx, cryptography" >nul 2>nul
if errorlevel 1 (
    echo Preparing the local Python environment...
    if not exist ".venv\Scripts\python.exe" (
        %GMC_PYTHON% -m venv .venv
        if errorlevel 1 goto :setup_failed
    )
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 goto :setup_failed
    set "GMC_PYTHON=.venv\Scripts\python.exe"
)

%GMC_PYTHON% local_launcher.py %*
set "GMC_EXIT=%errorlevel%"
if "%~1"=="" pause
exit /b %GMC_EXIT%

:setup_failed
echo Could not install the app's Python requirements. Check your internet connection and Python installation.
if "%~1"=="" pause
exit /b 1
