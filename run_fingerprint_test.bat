@echo off
title Fingerprint Device Tester
color 0A

echo.
echo ============================================
echo   FINGERPRINT DEVICE TESTER
echo ============================================
echo.
echo Starting test tool...
echo.

cd /d "%~dp0"

python test_fingerprint_devices.py

echo.
echo Test completed. Press any key to exit...
pause >nul