@echo off
setlocal

echo ============================================================
echo  CPH2451 (OnePlus 11) VIP FLASH - EDL Recovery
echo ============================================================
echo.
echo  Stock loader  : OP11-AUTO-RECOVER\flash_ready\prog_firehose_ddr.elf
echo  VIP loader    : Desktop\edl\Loaders\oppo\prog_firehose_ddr.elf
echo  Payloads      : workspace\payloads\rawprogram0-5.xml + patch0-5.xml
echo.
echo  BEFORE RUNNING:
echo    1. Device must be in EDL mode (Qualcomm HS-USB QDLoader 9008)
echo    2. Hold Vol+ + Vol- while plugging USB to enter EDL
echo    3. Verify COM port in workspace\config.py (default: COM7)
echo.

set MODE=--lun all
if "%1"=="--vip" set EXTRA=--vip
if "%1"=="--dryrun" set EXTRA=--dryrun
if "%1"=="--vip" if "%2"=="--dryrun" set EXTRA=--vip --dryrun

echo Running: python vip_flash.py %MODE% %EXTRA%
echo.

python "%~dp0vip_flash.py" %MODE% %EXTRA%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo  SUCCESS - All LUNs flashed. Disconnect and reconnect phone.
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo  FAILED - Check output above for errors.
    echo  Tip: Run with --vip flag if auth/loader error occurred.
    echo       python vip_flash.py --vip --lun all
    echo ============================================================
)

pause
endlocal
