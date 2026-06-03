@echo off
REM ============================================
REM  Fix Windows Firewall for GeoClean
REM  Right-click this file → Run as Administrator
REM ============================================
cd /d "%~dp0"

echo.
echo  Fixing firewall rules for GeoClean...
echo.

for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)"') do set PYTHON_PATH=%%P

echo  Python found at: %PYTHON_PATH%
echo.

REM Remove old rules
netsh advfirewall firewall delete rule name="GeoClean Python" >nul 2>&1
netsh advfirewall firewall delete rule name="Python (GeoClean)" >nul 2>&1

REM Add rule for ALL network profiles (public, private, domain)
netsh advfirewall firewall add rule name="GeoClean Python" dir=in action=allow program="%PYTHON_PATH%" profile=any enable=yes

if %errorlevel% equ 0 (
    echo.
    echo  ========================================
    echo   SUCCESS! Firewall rule added.
    echo   GeoClean will now launch without
    echo   admin prompts.
    echo  ========================================
) else (
    echo.
    echo  ERROR: Could not add firewall rule.
    echo  Make sure you right-clicked and chose
    echo  "Run as administrator"
)

echo.
pause
