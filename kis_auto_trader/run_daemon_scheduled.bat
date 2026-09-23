@echo off
rem Non-interactive daemon launcher for Windows Task Scheduler.
rem (2026-09-12) "자동매매 시작.bat" has a pause at the end, so it waits for a
rem keypress forever when run unattended. This one never blocks and writes all
rem output to logs\run_console.log instead.
cd /d "%~dp0"

set PY="C:\dev_python\python.exe"
if not exist %PY% set PY=python

echo. >> logs\run_console.log
echo [%date% %time%] scheduled daemon start >> logs\run_console.log
%PY% -u daemon.py >> logs\run_console.log 2>&1
echo [%date% %time%] daemon exited, code=%ERRORLEVEL% >> logs\run_console.log
