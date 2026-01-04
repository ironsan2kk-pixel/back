@echo off
chcp 65001 >nul
title TUI Admin Panel

echo ===============================================================
echo                     TUI ADMIN PANEL
echo                      Channel Access Bot
echo ===============================================================
echo.

:: Go to script directory
cd /d "%~dp0"
cd ..

:: Check virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo         Run install.bat first
    pause
    exit /b 1
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Run TUI admin
echo [*] Starting TUI admin panel...
echo.
python run_admin.py

:: If exited with error
if errorlevel 1 (
    echo.
    echo [ERROR] TUI admin panel crashed
    pause
)
