@echo off
REM Production startup script for Attendance System on Windows Server
REM Make sure to copy .env.example to .env and configure it properly

echo ===============================================
echo    Attendance System - Production Startup
echo ===============================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo ❌ Error: .env file not found!
    echo Please copy .env.example to .env and configure it properly.
    echo.
    pause
    exit /b 1
)

REM Set production environment
set FLASK_ENV=production
set FLASK_DEBUG=False

echo ✅ Environment: %FLASK_ENV%
echo ✅ Debug Mode: %FLASK_DEBUG%
echo.

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Start the application
echo 🚀 Starting Attendance System...
echo Press Ctrl+C to stop the server
echo.

python run.py

echo.
echo 🛑 Server stopped.
pause
