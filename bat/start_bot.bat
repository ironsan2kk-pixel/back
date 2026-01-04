@echo off
chcp 65001 >nul
title Channel Access Bot - Running

echo ===============================================================
echo                    CHANNEL ACCESS BOT
echo                       Starting bot
echo ===============================================================
echo.

:: Go to script directory
cd /d "%~dp0"
cd ..

:: Check .env
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo         Run install.bat first
    pause
    exit /b 1
)

:: Check virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo         Run install.bat first
    pause
    exit /b 1
)

:: Activate virtual environment
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat

:: Create PID file
echo %date% %time% > data\bot.pid

echo.
echo ===============================================================
echo   [STARTED] BOT IS RUNNING...
echo   
echo   To stop: press Ctrl+C or close this window
echo   Or use stop_bot.bat
echo ===============================================================
echo.

:: Run bot
python bot.py

:: If bot exited with error
if errorlevel 1 (
    echo.
    echo ===============================================================
    echo   [ERROR] BOT CRASHED!
    echo   
    echo   Check:
    echo   1. Token in .env file
    echo   2. Logs in logs\ folder
    echo   3. Internet connection
    echo ===============================================================
    pause
)

:: Remove PID file
if exist "data\bot.pid" del "data\bot.pid"
