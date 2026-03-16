@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  CPH2451 (OnePlus 11) - MASTER RECOVERY RUNNER
echo ============================================================
echo.
echo  Steps:
echo    1. Verify environment (Python, edlclient, paths)
echo    2. Check firmware files (all 6 LUNs)
echo    3. Reset USB / clear ghost devices
echo    4. Scan for EDL device
echo    5. Test EDL hello handshake
echo    6. Run VIP flash (all LUNs, with auto loader fallback)
echo.
echo  Press Ctrl+C at any time to abort.
echo ============================================================
echo.
pause

:: ---- Step 1: Verify environment ----
echo [1/6] Verifying environment...
python "%~dp0verify_env.py"
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Environment check failed. Fix Python/edlclient setup first.
    goto :ERROR
)
echo [OK] Environment verified.
echo.

:: ---- Step 2: Check firmware files ----
echo [2/6] Checking firmware files...
python "%~dp0check_firmware_files.py"
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Firmware files missing or incomplete.
    echo        Check FIRMWARE_ROOT in workspace\config.py.
    goto :ERROR
)
echo [OK] Firmware files present.
echo.

:: ---- Step 3: Reset USB ----
echo [3/6] Resetting USB (clearing ghost devices)...
pnputil /scan-devices >nul 2>&1
set DEVMGR_SHOW_NONPRESENT_DEVICES=1
pnputil /remove-device "USB\VID_05C6&PID_9008\5&1AE02F07&0&2" >nul 2>&1
pnputil /remove-device "USB\VID_05C6&PID_9008\5&1AE02F07&0&4" >nul 2>&1
pnputil /remove-device "USB\VID_05C6&PID_9008\5&1AE02F07&0&7" >nul 2>&1
pnputil /scan-devices >nul 2>&1
echo [OK] USB reset done.
echo.

:: ---- Step 4: Scan for EDL device ----
echo [4/6] Scanning for EDL device (QDLoader 9008)...
echo        If not found: Hold Vol+ + Vol- while plugging USB.
echo.

set FOUND=0
:SCAN_LOOP
python "%~dp0direct_usb_check.py" 2>nul | findstr /C:"EDL DEVICE FOUND" >nul
if %ERRORLEVEL% EQU 0 (
    set FOUND=1
    goto :DEVICE_FOUND
)
echo  Waiting for device... (Ctrl+C to abort)
timeout /t 3 /nobreak >nul
goto :SCAN_LOOP

:DEVICE_FOUND
echo [OK] EDL device detected.
echo.

:: ---- Step 5: Test EDL hello ----
echo [5/6] Testing EDL hello handshake...
python "%~dp0test_edl_hello.py"
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] EDL hello failed - device may still be flashable. Continuing...
) else (
    echo [OK] EDL hello passed.
)
echo.

:: ---- Step 6: VIP Flash ----
echo [6/6] Starting VIP flash (all 6 UFS LUNs)...
echo        This will flash the complete firmware. Do NOT unplug during flash.
echo.
pause

python "%~dp0vip_flash.py" --lun all
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo  ALL STEPS COMPLETE - DEVICE FLASHED SUCCESSFULLY
    echo  Disconnect USB, wait 10 seconds, reconnect. Device will boot.
    echo ============================================================
    goto :DONE
)

:ERROR
echo.
echo ============================================================
echo  RECOVERY FAILED
echo  Check logs above. Common fixes:
echo    - Re-enter EDL mode and run again
echo    - Run force_usb_reset.bat then retry
echo    - Check workspace\config.py PORT setting
echo    - Try: python vip_flash.py --vip --lun all
echo ============================================================
pause
exit /b 1

:DONE
pause
exit /b 0
