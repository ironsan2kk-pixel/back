@echo off
chcp 65001 >nul
title Install - Channel Access Bot

echo ===============================================================
echo                    INSTALL DEPENDENCIES
echo                      Channel Access Bot
echo ===============================================================
echo.

:: Go to project root (parent of bat folder)
cd /d "%~dp0"
cd ..
echo [INFO] Project folder: %cd%
echo.

:: Check Python
echo [*] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.11+
    echo         Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% found
echo.

:: Check requirements.txt exists
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found in project root!
    echo         Make sure requirements.txt is in: %cd%
    pause
    exit /b 1
)

:: Create virtual environment
if not exist "venv" (
    echo [*] Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)
echo.

:: Activate virtual environment
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat

:: Update pip
echo [*] Updating pip...
python -m pip install --upgrade pip --quiet

:: Install dependencies
echo [*] Installing dependencies from requirements.txt...
pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo ===============================================================
echo                    INSTALLATION COMPLETE!
echo ===============================================================
echo.

:: Create folders
echo [*] Creating folders...
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups
if not exist "data" mkdir data
echo [OK] Folders created
echo.

:: Check .env file
if not exist ".env" (
    echo [WARNING] .env file not found!
    echo [*] Creating .env from example...
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [OK] .env file created
        echo.
        echo [IMPORTANT] Open .env and fill in settings:
        echo    - BOT_TOKEN=your_bot_token
        echo    - CRYPTO_BOT_TOKEN=crypto_bot_token
        echo    - ADMIN_IDS=your_telegram_id
    ) else (
        echo [INFO] .env.example not found, skipping
    )
) else (
    echo [OK] .env file exists
)

echo.
echo ===============================================================
echo                       NEXT STEPS:
echo ===============================================================
echo.
echo   1. Edit .env file with your tokens
echo   2. Run start_bot.bat to start the bot
echo   3. Use start_admin.bat for TUI admin panel
echo.
echo ===============================================================
echo.
pause
