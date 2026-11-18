@echo off
setlocal EnableExtensions
title J.A.R.V.I.S AI Assistant Launcher
cd /d "%~dp0"

echo =====================================================
echo          J.A.R.V.I.S AI ASSISTANT LAUNCHER
echo =====================================================
echo.

set "VENV_PY=%~dp0venv\Scripts\python.exe"

REM -----------------------------------------------------
REM 1. Create virtual environment if it does not exist
REM -----------------------------------------------------
if not exist "%VENV_PY%" (
    echo [1/3] Virtual environment not found. Looking for Python...
    where py >nul 2>&1
    if %errorlevel%==0 (
        py -3 -m venv venv
    ) else (
        where python >nul 2>&1
        if %errorlevel%==0 (
            python -m venv venv
        ) else (
            echo.
            echo [ERROR] Python 3 is not installed or not in PATH.
            echo Please install Python 3.10+ from https://www.python.org/downloads/
            echo Make sure to check "Add Python to PATH" during installation.
            echo.
            pause
            exit /b 1
        )
    )
)

if not exist "%VENV_PY%" (
    echo [ERROR] Failed to create virtual environment in "%~dp0venv".
    pause
    exit /b 1
)

REM -----------------------------------------------------
REM 2. Check and install requirements if missing
REM -----------------------------------------------------
set "NEED_INSTALL=0"
if /I "%~1"=="--reinstall" set "NEED_INSTALL=1"

if "%NEED_INSTALL%"=="0" (
    "%VENV_PY%" -c "import PySide6, google.genai, groq, dotenv, requests, psutil, edge_tts, pygame" >nul 2>&1
    if errorlevel 1 set "NEED_INSTALL=1"
)

if "%NEED_INSTALL%"=="1" (
    echo [2/3] Installing required Python packages from requirements.txt...
    "%VENV_PY%" -m pip install --upgrade pip
    "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install requirements. Check your internet connection.
        echo.
        pause
        exit /b 1
    )
    echo Requirements installed successfully!
) else (
    echo [2/3] All required packages are already installed.
)

REM -----------------------------------------------------
REM 3. Create starter .env if missing (never overwrites existing)
REM -----------------------------------------------------
if not exist "%~dp0.env" (
    echo [INFO] Creating starter .env file...
    (
        echo GEMINI_API_KEY=
        echo GROQ_API_KEY=
        echo OLLAMA_URL=http://localhost:11434
        echo OLLAMA_MODEL=qwen3.5:4b
    ) > "%~dp0.env"
    echo [NOTE] Add your GEMINI_API_KEY / GROQ_API_KEY in .env for cloud AI providers.
)

REM -----------------------------------------------------
REM 4. Launch J.A.R.V.I.S GUI
REM -----------------------------------------------------
echo [3/3] Starting J.A.R.V.I.S AI Assistant...
echo.
"%VENV_PY%" -m interface.chat
set "EXIT_CODE=%errorlevel%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] J.A.R.V.I.S exited with code %EXIT_CODE%.
    pause
    exit /b %EXIT_CODE%
)

endlocal

