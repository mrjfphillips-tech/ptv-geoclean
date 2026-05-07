@echo off
REM ============================================
REM  GeoClean — Launch Application
REM ============================================
cd /d "%~dp0"

echo.
echo  ========================================
echo   GeoClean - Fuzzy Geocoding
echo  ========================================
echo.

REM Start the server in the background, then open browser
start /min "" python -m streamlit run app.py --server.headless false

REM Wait for server to start, then open browser
timeout /t 4 /nobreak >nul
start http://localhost:8501

exit
