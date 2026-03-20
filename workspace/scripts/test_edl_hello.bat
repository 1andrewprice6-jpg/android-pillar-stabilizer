@echo off
setlocal
cd /d "%~dp0"
echo Testing basic EDL communication on COM5...
python test_edl_hello.py
pause
endlocal
