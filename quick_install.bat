@echo off
REM Quick install script using requirements.txt
REM This is the simplest way to install all dependencies

echo ===============================================
echo    Quick Install - All Dependencies
echo ===============================================
echo.

echo 🔍 Checking Python...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.8+ first.
    pause
    exit /b 1
)

echo.
echo 📦 Installing all dependencies from requirements.txt...
echo.

REM Upgrade pip first
python -m pip install --upgrade pip

REM Install from requirements.txt
pip install -r requirements.txt

echo.
echo 🔍 Testing critical imports...
python -c "import flask; print('✅ Flask: OK')" 2>nul || echo "❌ Flask: FAILED"
python -c "import pyodbc; print('✅ pyodbc: OK')" 2>nul || echo "❌ pyodbc: FAILED"
python -c "import pandas; print('✅ pandas: OK')" 2>nul || echo "❌ pandas: FAILED"

echo.
if exist ".env" (
    echo ✅ .env file exists
) else (
    echo ⚠️  .env file not found - copy from .env.example
)

echo.
echo 🎉 Installation completed!
echo Run: python test_database.py
echo.
pause
