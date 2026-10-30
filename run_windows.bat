@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Expense Manager needs first-time setup.
    call setup_windows.bat
    if errorlevel 1 exit /b 1
)

if not exist ".env" (
    echo Local settings are missing. Running setup again...
    call setup_windows.bat
    if errorlevel 1 exit /b 1
)

echo.
echo Starting Expense Manager...
echo Open http://127.0.0.1:5000 in your browser.
echo Keep this window open. Press Ctrl+C to stop the app.
echo.
".venv\Scripts\python.exe" -m flask --app run run --debug

echo.
echo Expense Manager stopped.
pause
