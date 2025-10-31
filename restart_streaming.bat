@echo off
REM ================================================================================
REM Streaming Service Restart Script for Windows Task Scheduler
REM ================================================================================
REM This script will:
REM 1. Stop the streaming service
REM 2. Wait for 20 seconds
REM 3. Start the streaming service again
REM
REM Usage: Can be run manually or through Windows Task Scheduler
REM Author: Generated for Attendance System
REM Date: %date% %time%
REM ================================================================================

echo.
echo ========================================================
echo    Streaming Service Restart Script
echo ========================================================
echo Start Time: %date% %time%
echo.

REM Configuration
set FLASK_HOST=127.0.0.1
set FLASK_PORT=5000
set BASE_URL=http://%FLASK_HOST%:%FLASK_PORT%
set STOP_URL=%BASE_URL%/sync/streaming/stop
set START_URL=%BASE_URL%/sync/streaming/start
set STATUS_URL=%BASE_URL%/sync/streaming/status
set WAIT_SECONDS=20

echo Configuration:
echo - Flask Host: %FLASK_HOST%
echo - Flask Port: %FLASK_PORT%
echo - Stop URL: %STOP_URL%
echo - Start URL: %START_URL%
echo - Wait Time: %WAIT_SECONDS% seconds
echo.

REM Check if curl is available
curl --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: curl is not available on this system
    echo Please install curl or use PowerShell version of this script
    echo.
    goto :error_exit
)

REM Step 1: Check current streaming status
echo 🔍 Step 1: Checking current streaming status...
curl -s -X GET "%STATUS_URL%" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Cannot connect to Flask application at %BASE_URL%
    echo Please make sure the Attendance System is running
    echo.
    goto :error_exit
)
echo ✅ Flask application is accessible
echo.

REM Step 2: Stop streaming service
echo 🛑 Step 2: Stopping streaming service...
echo Request: POST %STOP_URL%
curl -s -X POST "%STOP_URL%" -H "Content-Type: application/json" -d "{}" >temp_stop_response.txt 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Failed to stop streaming service
    if exist temp_stop_response.txt type temp_stop_response.txt
    goto :cleanup_error
)

echo ✅ Stop request sent successfully
if exist temp_stop_response.txt (
    echo Response:
    type temp_stop_response.txt
    del temp_stop_response.txt
)
echo.

REM Step 3: Wait for 20 seconds
echo ⏳ Step 3: Waiting for %WAIT_SECONDS% seconds...
echo Starting countdown...

REM Countdown display
for /l %%i in (%WAIT_SECONDS%,-1,1) do (
    <nul set /p =Remaining: %%i seconds... 
    timeout /t 1 /nobreak >nul
    echo.
)
echo ✅ Wait period completed
echo.

REM Step 4: Start streaming service
echo 🚀 Step 4: Starting streaming service...
echo Request: POST %START_URL%
curl -s -X POST "%START_URL%" -H "Content-Type: application/json" -d "{}" >temp_start_response.txt 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Failed to start streaming service
    if exist temp_start_response.txt type temp_start_response.txt
    goto :cleanup_error
)

echo ✅ Start request sent successfully
if exist temp_start_response.txt (
    echo Response:
    type temp_start_response.txt
    del temp_start_response.txt
)
echo.

REM Step 5: Verify streaming status
echo 🔍 Step 5: Verifying streaming status...
curl -s -X GET "%STATUS_URL%" >temp_status_response.txt 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  WARNING: Could not verify streaming status
    if exist temp_status_response.txt type temp_status_response.txt
    goto :cleanup_warning
)

echo ✅ Status check completed
if exist temp_status_response.txt (
    echo Current Status:
    type temp_status_response.txt
    del temp_status_response.txt
)
echo.

REM Success completion
echo ========================================================
echo ✅ STREAMING RESTART COMPLETED SUCCESSFULLY
echo ========================================================
echo End Time: %date% %time%
echo.
echo Operations performed:
echo 1. ✅ Stopped streaming service
echo 2. ✅ Waited %WAIT_SECONDS% seconds
echo 3. ✅ Started streaming service
echo 4. ✅ Verified status
echo.

REM Clean exit
if exist temp_*.txt del temp_*.txt
exit /b 0

REM Error handling
:cleanup_error
if exist temp_*.txt del temp_*.txt
:error_exit
echo ========================================================
echo ❌ STREAMING RESTART FAILED
echo ========================================================
echo End Time: %date% %time%
echo.
echo Please check:
echo 1. Attendance System is running on %BASE_URL%
echo 2. Streaming service is properly configured
echo 3. Network connectivity is working
echo 4. curl is installed and accessible
echo.
exit /b 1

:cleanup_warning
if exist temp_*.txt del temp_*.txt
echo ========================================================
echo ⚠️  STREAMING RESTART COMPLETED WITH WARNINGS
echo ========================================================
echo End Time: %date% %time%
echo.
echo The restart operations were performed but status verification failed
echo Please check the streaming service manually through the web interface
echo.
exit /b 2