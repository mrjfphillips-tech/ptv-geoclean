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
echo  Starting GeoClean...
echo  (Browser will open automatically)
echo.

python launch.py
