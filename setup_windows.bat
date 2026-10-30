@echo off
setlocal
cd /d "%~dp0"

echo.
echo ========================================
echo   Expense Manager - First-time setup
echo ========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python Launcher was not found.
    echo Install Python 3.12 from https://www.python.org/downloads/
    echo During installation, tick "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating the Python environment...
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo Python 3.12 was not found. Trying your default Python 3...
        py -3 -m venv .venv
    )
    if errorlevel 1 goto :failed
) else (
    echo [1/4] Python environment already exists.
)

echo [2/4] Installing required packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo [3/4] Preparing local settings...
if not exist ".env" copy ".env.example" ".env" >nul
".venv\Scripts\python.exe" -c "from pathlib import Path; import secrets; p=Path('.env'); s=p.read_text(encoding='utf-8'); p.write_text(s.replace('SECRET_KEY=\n', 'SECRET_KEY='+secrets.token_hex(32)+'\n', 1), encoding='utf-8')"
if errorlevel 1 goto :failed

echo [4/4] Creating the database...
".venv\Scripts\python.exe" -m flask --app run init-db
if errorlevel 1 goto :failed

echo.
echo Setup completed successfully.
echo Double-click run_windows.bat to start Expense Manager.
pause
exit /b 0

:failed
echo.
echo Setup failed. Keep this window open and send a screenshot of the error.
pause
exit /b 1
