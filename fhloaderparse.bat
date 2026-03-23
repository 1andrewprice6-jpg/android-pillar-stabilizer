@echo off
title Firehose Loader Parser
setlocal EnableDelayedExpansion

:: Locate edl tool: check PATH first, then common install locations
set EDL_PY=
where edl >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set EDL_CMD=edl
    goto :found_edl
)
for %%D in (
    "%USERPROFILE%\edl\edl.py"
    "%USERPROFILE%\Desktop\edl-master\edl-master\edl.py"
    "%USERPROFILE%\Desktop\edl\edl.py"
    "%~dp0edl\edl.py"
    "%~dp0edl.py"
) do (
    if exist %%D (
        set EDL_PY=%%D
        set EDL_CMD=python !EDL_PY!
        goto :found_edl
    )
)
echo [ERROR] edl tool not found.
echo   Install with:  pip install edl
echo   Or clone:      git clone https://github.com/bkerler/edl.git %%USERPROFILE%%\edl
pause
exit /b 1

:found_edl
echo [INFO] Using EDL tool: %EDL_CMD%
:: Parse/print supported functions from the connected Firehose loader
%EDL_CMD% printgpt --memory=ufs %*
