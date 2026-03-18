@echo off
setlocal

echo ============================================================
echo  DRIVER SETUP - Qualcomm QDLoader 9008 (EDL Mode)
echo ============================================================
echo.
echo  libusb cannot open the device until the Windows driver is
echo  replaced with WinUSB. This is a one-time setup step.
echo.
echo  STEPS:
echo.
echo  1. Put phone into EDL mode FIRST:
echo     - Hold Vol+ + Vol- simultaneously
echo     - Plug in USB while holding
echo     - Device should appear in Device Manager as:
echo       "Qualcomm HS-USB QDLoader 9008" (under Ports or Unknown)
echo.
echo  2. Zadig will open automatically below.
echo     In Zadig:
echo     a) Options menu -> "List All Devices"
echo     b) Select "QHSUSB_BULK" or "Qualcomm HS-USB QDLoader 9008"
echo     c) In the driver dropdown, select "WinUSB"
echo     d) Click "Install Driver" or "Replace Driver"
echo     e) Wait for install to complete (may take 30-60 seconds)
echo.
echo  3. After Zadig is done, re-run run_all.bat
echo.
echo ============================================================
echo.

:: Check bundled Zadig first (extracted from edl-master.zip)
set ZADIG_PATH=
if exist "C:\Users\Andrew Price\Desktop\edl\Drivers\Windows\zadig-2.8.exe" (
    set ZADIG_PATH=C:\Users\Andrew Price\Desktop\edl\Drivers\Windows\zadig-2.8.exe
)

:: Fallback locations
if not defined ZADIG_PATH if exist "C:\Program Files\Zadig\zadig.exe" set ZADIG_PATH=C:\Program Files\Zadig\zadig.exe
if not defined ZADIG_PATH (
    where zadig.exe >nul 2>&1
    if %ERRORLEVEL% EQU 0 for /f "delims=" %%i in ('where zadig.exe') do set ZADIG_PATH=%%i
)

if defined ZADIG_PATH (
    echo [INFO] Launching Zadig: %ZADIG_PATH%
    start "" "%ZADIG_PATH%"
) else (
    echo [WARN] Zadig not found. Run: winget install akeo.ie.Zadig
)

echo.
echo After installing the WinUSB driver in Zadig, press any key to run the full driver status check...
pause >nul

:: Run driver status checker
echo.
echo Running driver status checker...
powershell -ExecutionPolicy Bypass -File "%~dp0check_driver_status.ps1"

pause
endlocal
