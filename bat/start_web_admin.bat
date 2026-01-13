@echo off
chcp 65001 >nul
title Web Admin Panel

echo ===============================================================
echo                     WEB ADMIN PANEL
echo                      Channel Access Bot
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
call venv\Scripts\activate.bat

echo [*] Starting Web admin panel...
echo.
python run_web_admin.py

if errorlevel 1 (
    echo.
    echo [ERROR] Web admin panel crashed
    pause
)
