@echo off
echo Attempting to reset USB connection for Qualcomm device...
devcon restart "USB\VID_05C6&PID_9008*"
if %errorlevel% neq 0 (
    echo [WARNING] devcon not found or failed. Please physically unplug and replug the device.
) else (
    echo [SUCCESS] Device reset command sent.
)
pause
