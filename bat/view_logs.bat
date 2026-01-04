@echo off
chcp 65001 >nul
title View Logs

echo ===============================================================
echo                       VIEW LOGS
echo                      Channel Access Bot
echo ===============================================================
echo.

cd /d "%~dp0"
cd ..

if not exist "logs" (
    echo [ERROR] logs folder not found
    pause
    exit /b 1
)

:MENU
echo.
echo Select action:
echo.
echo   [1] Show last 50 lines of current log
echo   [2] Watch logs in real-time (tail -f)
echo   [3] Open logs folder
echo   [4] List all logs
echo   [5] Clean old logs (older than 7 days)
echo   [0] Exit
echo.
set /p CHOICE="Your choice (0-5): "

if "%CHOICE%"=="1" goto TAIL50
if "%CHOICE%"=="2" goto TAILF
if "%CHOICE%"=="3" goto OPEN
if "%CHOICE%"=="4" goto LIST
if "%CHOICE%"=="5" goto CLEANUP
if "%CHOICE%"=="0" goto EXIT
goto MENU

:TAIL50
echo.
echo [INFO] Last 50 lines of log:
echo ---------------------------------------------------------------
:: Find latest log
for /f "delims=" %%F in ('dir /b /o-d logs\bot_*.log 2^>nul') do (
    set LATEST_LOG=logs\%%F
    goto :SHOW_TAIL
)
echo [ERROR] No logs found
pause
goto MENU

:SHOW_TAIL
echo File: %LATEST_LOG%
echo ---------------------------------------------------------------
powershell -Command "Get-Content '%LATEST_LOG%' -Tail 50"
echo ---------------------------------------------------------------
pause
goto MENU

:TAILF
echo.
echo [INFO] Watching logs in real-time...
echo        (Press Ctrl+C to exit)
echo ---------------------------------------------------------------

for /f "delims=" %%F in ('dir /b /o-d logs\bot_*.log 2^>nul') do (
    set LATEST_LOG=logs\%%F
    goto :START_TAIL
)
echo [ERROR] No logs found
pause
goto MENU

:START_TAIL
powershell -Command "Get-Content '%LATEST_LOG%' -Wait -Tail 20"
goto MENU

:OPEN
echo.
echo [*] Opening logs folder...
explorer logs
goto MENU

:LIST
echo.
echo [INFO] Log files:
echo ---------------------------------------------------------------
dir /o-d logs\*.log
echo ---------------------------------------------------------------
pause
goto MENU

:CLEANUP
echo.
echo [*] Deleting logs older than 7 days...
forfiles /p logs /s /m *.log /d -7 /c "cmd /c del @path" 2>nul
echo [OK] Cleanup complete
pause
goto MENU

:EXIT
exit /b 0
