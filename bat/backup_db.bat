@echo off
chcp 65001 >nul
title Database Backup

echo ===============================================================
echo                    DATABASE BACKUP
echo                      Channel Access Bot
echo ===============================================================
echo.

:: Go to project directory
cd /d "%~dp0"
cd ..

:: Create backup folder
if not exist "backups" mkdir backups

:: Check database exists
if not exist "data\bot.db" (
    echo [ERROR] Database not found: data\bot.db
    pause
    exit /b 1
)

:: Create backup filename with timestamp
set TIMESTAMP=%date:~6,4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set BACKUP_FILE=backups\backup_%TIMESTAMP%.db

:: Copy database file
echo [*] Creating backup...
copy "data\bot.db" "%BACKUP_FILE%" >nul

if errorlevel 1 (
    echo [ERROR] Backup failed!
    pause
    exit /b 1
)

echo [OK] Backup created: %BACKUP_FILE%

:: Get file size
for %%A in ("%BACKUP_FILE%") do set SIZE=%%~zA
set /a SIZE_KB=%SIZE%/1024
echo [INFO] Size: %SIZE_KB% KB

:: Delete old backups (keep last 7)
echo.
echo [*] Cleaning old backups...
set COUNT=0
for /f "skip=7 delims=" %%F in ('dir /b /o-d backups\backup_*.db 2^>nul') do (
    del "backups\%%F"
    set /a COUNT+=1
)
if %COUNT% GTR 0 echo [OK] Deleted old backups: %COUNT%

:: List existing backups
echo.
echo [INFO] Existing backups:
echo ---------------------------------------------------------------
dir /b /o-d backups\backup_*.db 2>nul
echo ---------------------------------------------------------------

echo.
echo ===============================================================
echo                    BACKUP COMPLETE
echo ===============================================================
echo.
timeout /t 5
