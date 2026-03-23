@echo off
title FastPwn - Fastboot Exploit / EDL Unlock
setlocal EnableDelayedExpansion

:: fastpwn.exe is a pre-built binary shipped with some bkerler/edl releases.
:: Look for it next to this script, in the edl directory, or on PATH.
set FASTPWN_EXE=
where fastpwn >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set FASTPWN_EXE=fastpwn
    goto :found_fp
)
for %%F in (
    "%~dp0fastpwn.exe"
    "%~dp0fastpwn"
    "%USERPROFILE%\edl\fastpwn.exe"
    "%USERPROFILE%\Desktop\edl-master\edl-master\fastpwn.exe"
) do (
    if exist %%F (
        set FASTPWN_EXE=%%F
        goto :found_fp
    )
)

:: Fallback: use edl tool's fasboot exploit command
where edl >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] fastpwn.exe not found, using: edl fastboot
    edl fastboot %*
    exit /b %ERRORLEVEL%
)

echo [ERROR] Neither fastpwn.exe nor edl tool found.
echo   Install edl with:  pip install edl
pause
exit /b 1

:found_fp
echo [INFO] Using: %FASTPWN_EXE%
%FASTPWN_EXE% %*
