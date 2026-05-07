@echo off
REM ============================================
REM  GeoClean — One-Click Setup
REM  Fuzzy Geocoding with Confidence
REM ============================================
echo.
echo  ========================================
echo   GeoClean - Setup Wizard
echo   Fuzzy Geocoding with Confidence
echo  ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.10+ from:
    echo   https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo [1/3] Python found:
python --version
echo.

REM Install dependencies
echo [2/3] Installing required packages...
echo.
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo WARNING: Some packages may have failed. Trying again...
    pip install pandas requests rapidfuzz streamlit openpyxl python-dotenv
)
echo.
echo      Done!
echo.

REM Check for .env file
if not exist ".env" (
    echo [3/3] Creating .env configuration file...
    echo.
    echo  You need an Azure Maps API key to use geocoding.
    echo  Get one free at: https://portal.azure.com
    echo    1. Search "Azure Maps"
    echo    2. Create a new Azure Maps Account (free tier = 5000 calls/day)
    echo    3. Go to Authentication tab
    echo    4. Copy the "Primary Key"
    echo.
    set /p AZURE_KEY="  Paste your Azure Maps key here (or press Enter to skip): "
    if defined AZURE_KEY (
        echo AZURE_MAPS_KEY=%AZURE_KEY%> .env
        echo.
        echo      API key saved to .env
    ) else (
        copy .env.example .env >nul
        echo.
        echo      Skipped. Edit the .env file later with your key.
    )
) else (
    echo [3/3] .env file already exists. Good!
)

echo.
echo  ========================================
echo   SETUP COMPLETE!
echo  ========================================
echo.
echo  To launch GeoClean:
echo    Double-click "LAUNCH.bat"
echo    OR run: streamlit run app.py
echo.
echo  The app will open in your web browser.
echo.
pause
