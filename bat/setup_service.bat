@echo off
chcp 65001 >nul
title Windows Service Setup

echo ===============================================================
echo                  WINDOWS SERVICE SETUP
echo                     Channel Access Bot
echo ===============================================================
echo.

:: Check admin rights
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Administrator rights required!
    echo         Run this file as Administrator.
    pause
    exit /b 1
)

:: Go to project directory
cd /d "%~dp0"
cd ..
set PROJECT_DIR=%cd%

echo [INFO] Project directory: %PROJECT_DIR%
echo.

:MENU
echo Select action:
echo.
echo   [1] Install NSSM and create service
echo   [2] Start service
echo   [3] Stop service
echo   [4] Remove service
echo   [5] Service status
echo   [0] Exit
echo.
set /p CHOICE="Your choice (0-5): "

if "%CHOICE%"=="1" goto INSTALL
if "%CHOICE%"=="2" goto START
if "%CHOICE%"=="3" goto STOP
if "%CHOICE%"=="4" goto REMOVE
if "%CHOICE%"=="5" goto STATUS
if "%CHOICE%"=="0" goto EXIT
goto MENU

:INSTALL
echo.
echo ===============================================================
echo                    INSTALLING SERVICE
echo ===============================================================
echo.

:: Check NSSM exists
if not exist "tools\nssm.exe" (
    echo [WARNING] NSSM not found!
    echo.
    echo    Download NSSM from: https://nssm.cc/download
    echo    Extract nssm.exe to tools\ folder
    echo.
    echo    Or install via Chocolatey:
    echo    choco install nssm
    echo.
    pause
    goto MENU
)

:: Service name
set SERVICE_NAME=ChannelAccessBot

:: Python path in venv
set PYTHON_PATH=%PROJECT_DIR%\venv\Scripts\python.exe
set BOT_PATH=%PROJECT_DIR%\bot.py

:: Check files exist
if not exist "%PYTHON_PATH%" (
    echo [ERROR] Python not found: %PYTHON_PATH%
    echo         Run install.bat first
    pause
    goto MENU
)

if not exist "%BOT_PATH%" (
    echo [ERROR] bot.py not found: %BOT_PATH%
    pause
    goto MENU
)

:: Create service via NSSM
echo [*] Creating service %SERVICE_NAME%...

tools\nssm.exe install %SERVICE_NAME% "%PYTHON_PATH%"
tools\nssm.exe set %SERVICE_NAME% AppParameters "%BOT_PATH%"
tools\nssm.exe set %SERVICE_NAME% AppDirectory "%PROJECT_DIR%"
tools\nssm.exe set %SERVICE_NAME% DisplayName "Channel Access Bot"
tools\nssm.exe set %SERVICE_NAME% Description "Telegram bot for selling channel access"
tools\nssm.exe set %SERVICE_NAME% Start SERVICE_AUTO_START
tools\nssm.exe set %SERVICE_NAME% AppStdout "%PROJECT_DIR%\logs\service_stdout.log"
tools\nssm.exe set %SERVICE_NAME% AppStderr "%PROJECT_DIR%\logs\service_stderr.log"
tools\nssm.exe set %SERVICE_NAME% AppRotateFiles 1
tools\nssm.exe set %SERVICE_NAME% AppRotateBytes 10485760

echo.
echo [OK] Service created!
echo.
echo    Name: %SERVICE_NAME%
echo    Auto-start: Yes
echo.
echo    Management:
echo    - Start:    net start %SERVICE_NAME%
echo    - Stop:     net stop %SERVICE_NAME%
echo    - Remove:   nssm remove %SERVICE_NAME%
echo.
pause
goto MENU

:START
echo.
echo [*] Starting service...
net start ChannelAccessBot
if errorlevel 1 (
    echo [ERROR] Failed to start service
) else (
    echo [OK] Service started
)
pause
goto MENU

:STOP
echo.
echo [*] Stopping service...
net stop ChannelAccessBot
if errorlevel 1 (
    echo [ERROR] Failed to stop service
) else (
    echo [OK] Service stopped
)
pause
goto MENU

:REMOVE
echo.
echo [WARNING] Are you sure you want to remove service? (y/n)
set /p CONFIRM=
if /i "%CONFIRM%"=="y" (
    net stop ChannelAccessBot >nul 2>&1
    if exist "tools\nssm.exe" (
        tools\nssm.exe remove ChannelAccessBot confirm
    ) else (
        sc delete ChannelAccessBot
    )
    echo [OK] Service removed
) else (
    echo Cancelled
)
pause
goto MENU

:STATUS
echo.
echo [INFO] Service status:
sc query ChannelAccessBot
pause
goto MENU

:EXIT
exit /b 0
