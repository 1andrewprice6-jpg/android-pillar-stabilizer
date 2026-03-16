@echo off
echo ====================================
echo FORCE USB DEVICE RESET
echo ====================================
echo.

echo Disabling Qualcomm 9008 devices...
for /f "tokens=*" %%i in ('pnputil /enum-devices /class Ports /connected ^| findstr /C:"9008"') do (
    echo Found: %%i
)

echo.
echo Restarting all USB Root Hubs to force re-enumeration...
pnputil /scan-devices

echo.
echo Removing ghost/phantom devices...
set DEVMGR_SHOW_NONPRESENT_DEVICES=1
pnputil /remove-device "USB\VID_05C6&PID_9008\5&1AE02F07&0&2" 2>nul
pnputil /remove-device "USB\VID_05C6&PID_9008\5&1AE02F07&0&4" 2>nul
pnputil /remove-device "USB\VID_05C6&PID_9008\5&1AE02F07&0&7" 2>nul

echo.
echo Re-scanning for hardware changes...
pnputil /scan-devices

timeout /t 3 /nobreak >nul

echo.
echo Current QDLoader devices:
pnputil /enum-devices /class Ports /connected | findstr /C:"9008"

echo.
echo ====================================
echo NOW: Physically disconnect and reconnect the phone
echo      Hold BOTH volume buttons while plugging in USB
echo ====================================
pause
