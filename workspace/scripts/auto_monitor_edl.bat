@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo EDL MODE RECOVERY - AUTO MONITOR
echo ============================================================
echo.
echo This script will continuously monitor for the EDL device
echo and automatically run the unbrick script when detected.
echo.
echo Instructions:
echo 1. Keep this window open
echo 2. Disconnect your OnePlus 11 completely
echo 3. Hold VOLUME UP + VOLUME DOWN together
echo 4. While holding, plug in the USB cable
echo 5. Keep holding for 3-5 seconds
echo 6. Device should enter EDL mode (Qualcomm HS-USB QDLoader 9008)
echo.
echo Press Ctrl+C to stop monitoring
echo ============================================================
echo.

:MONITOR_LOOP
cls
echo [%TIME%] Scanning for EDL device...

python direct_usb_check.py 2>nul | findstr /C:"EDL DEVICE FOUND" >nul
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo [SUCCESS] EDL DEVICE DETECTED!
    echo ============================================================
    echo.
    timeout /t 2 /nobreak >nul

    echo Running unbrick script...
    python ULTIMATE_UNBRICK_REAL.py

    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ============================================================
        echo [SUCCESS] Unbrick completed!
        echo ============================================================
        pause
        exit /b 0
    ) else (
        echo.
        echo [ERROR] Unbrick failed - retrying in 5 seconds...
        timeout /t 5 /nobreak >nul
        goto MONITOR_LOOP
    )
)

REM Check if device shows in Device Manager but not accessible
for /f "tokens=*" %%i in ('pnputil /enum-devices /class Ports 2^>nul ^| findstr /C:"9008"') do (
    echo [DETECTED] Device in system but not accessible - attempting reset...
    pnputil /scan-devices >nul 2>&1
)

timeout /t 2 /nobreak >nul
goto MONITOR_LOOP
