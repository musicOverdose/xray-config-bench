@echo off
rem ==============================================================================
rem Xray Config Bench — Windows Batch Launcher
rem ==============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo [Xray Config Bench] Initializing application on Windows...

rem Check Python availability
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    where py >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Python 3 was not found in PATH.
        echo Please install Python 3.10+ from https://www.python.org/
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    ) else (
        set "PY_CMD=py -3"
    )
) else (
    set "PY_CMD=python"
)

rem Check virtual environment
if not exist ".venv\Scripts\activate.bat" (
    echo [Xray Config Bench] Creating Python virtual environment in .venv...
    %PY_CMD% -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    call .venv\Scripts\activate.bat
    echo [Xray Config Bench] Installing required dependencies...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b 1
    )
) else (
    call .venv\Scripts\activate.bat
)

rem Launch GUI application
echo [Xray Config Bench] Launching desktop interface...
start "" pythonw main.py %*
if %ERRORLEVEL% neq 0 (
    python main.py %*
)
