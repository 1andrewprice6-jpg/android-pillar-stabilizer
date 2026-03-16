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

:: Try to find Zadig in common locations
set ZADIG_PATH=
if exist "C:\Program Files\Zadig\zadig.exe" set ZADIG_PATH=C:\Program Files\Zadig\zadig.exe
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Packages\Akeo.Zadig_*\zadig.exe" (
    for /f "delims=" %%i in ('dir /b /s "%LOCALAPPDATA%\Microsoft\WinGet\Packages\Akeo.Zadig_*\zadig.exe" 2^>nul') do set ZADIG_PATH=%%i
)
if exist "%ProgramFiles%\Zadig\zadig.exe" set ZADIG_PATH=%ProgramFiles%\Zadig\zadig.exe

:: Also check PATH
where zadig.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "delims=" %%i in ('where zadig.exe') do set ZADIG_PATH=%%i
)

if defined ZADIG_PATH (
    echo [INFO] Found Zadig at: %ZADIG_PATH%
    echo [INFO] Launching Zadig...
    start "" "%ZADIG_PATH%"
) else (
    echo [WARN] Zadig not found in standard locations.
    echo.
    echo  To install Zadig:
    echo    winget install akeo.ie.Zadig
    echo.
    echo  Or download from: https://zadig.akeo.ie/
    echo  Run: install_edl_win10_win11.ps1 (in Desktop\edl\) to auto-install.
)

echo.
echo After installing the WinUSB driver in Zadig, press any key to verify...
pause >nul

:: Verify the device is now accessible
echo.
echo Checking if EDL device is accessible via libusb...
python -c "import usb.core; d=usb.core.find(idVendor=0x05C6,idProduct=0x9008); print('[OK] Device accessible!' if d else '[FAIL] Device not found - ensure phone is in EDL mode')"
echo.
pause
endlocal
