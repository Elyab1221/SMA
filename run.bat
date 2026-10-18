@echo off
title Cyber Talent Club SMA
cd /d "%~dp0"

echo ==========================================================
echo    Launching Cyber Talent Club SMA Server...
echo ==========================================================
echo.

:: Automatically open browser after 2 seconds in the background
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:5000"

:: Start the Flask app
python app.py

:: If it exits with error, pause so the window does not close
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The server stopped unexpectedly.
    pause
)
