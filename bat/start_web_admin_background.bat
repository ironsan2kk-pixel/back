@echo off
chcp 65001 >nul
title Web Admin Panel (Background)

cd /d "%~dp0"
cd ..

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo         Run install.bat first
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

start "Web Admin Panel" /min cmd /c python run_web_admin.py

echo [OK] Web admin panel started in background.
