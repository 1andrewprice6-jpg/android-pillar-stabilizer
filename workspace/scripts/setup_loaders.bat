@echo off
setlocal

echo ============================================================
echo  SETUP: bkerler/Loaders - Qualcomm Firehose Loader Database
echo ============================================================
echo.
echo  Clones https://github.com/bkerler/Loaders.git into:
echo  C:\Users\Andrew Price\Desktop\edl\Loaders\bkerler
echo.
echo  The loader_db.py in edlclient auto-scans Desktop\edl\Loaders\
echo  for device-specific loaders keyed by HWID + public key hash.
echo  Having the right SM8550 loader is required for Sahara upload.
echo.

set LOADERS_DEST=C:\Users\Andrew Price\Desktop\edl\Loaders\bkerler
set LOADERS_REPO=https://github.com/bkerler/Loaders.git

if exist "%LOADERS_DEST%\.git" (
    echo [INFO] Loaders repo already cloned. Pulling latest...
    git -C "%LOADERS_DEST%" pull --ff-only
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Loaders updated.
    ) else (
        echo [WARN] Pull failed - repo may be ahead or have conflicts.
    )
    goto :DONE
)

echo [INFO] Cloning %LOADERS_REPO%...
echo        This may take a few minutes (repo is large).
echo.
git clone --depth=1 "%LOADERS_REPO%" "%LOADERS_DEST%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Loaders cloned to: %LOADERS_DEST%
    echo.
    echo Checking for SM8550 / CPH2451 loaders...
    dir /b "%LOADERS_DEST%\oppo\*8550*" 2>nul
    dir /b "%LOADERS_DEST%\oppo\*SM8550*" 2>nul
    dir /b "%LOADERS_DEST%\oneplus\*8550*" 2>nul
    dir /b "%LOADERS_DEST%\oneplus\*SM8550*" 2>nul
    dir /b "%LOADERS_DEST%\oppo\*CPH2451*" 2>nul
    echo.
    echo [DONE] Now re-run run_all.bat - edlclient will auto-select the
    echo        correct loader based on your device HWID and public key hash.
) else (
    echo.
    echo [FAIL] Clone failed. Check your internet connection and git install.
    echo        Manual clone: git clone --depth=1 %LOADERS_REPO% "%LOADERS_DEST%"
)

:DONE
echo.
pause
endlocal
