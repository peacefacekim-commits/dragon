@echo off
rem Registers the data-collection daemon with Windows Task Scheduler so it
rem starts by itself every weekday - no more launching it by hand.
rem
rem Schedule: fires at 08:50, then retries every hour until 19:50.
rem   - The hourly retry is the self-healing part: if the PC was asleep or off
rem     at 08:50, the next hourly trigger picks it up instead of losing the day.
rem   - Re-triggering while it is already running is harmless: daemon.py holds
rem     a lock file and the second instance exits immediately.
rem   - Weekends are handled inside daemon.py (it exits right away).
rem   - (2026-09-13) The window now reaches 19:50 instead of 15:50. daemon.py
rem     collects the daily price panel AFTER the close, so a PC that only
rem     comes online in the evening can still save that day's panel data -
rem     it just skips the intraday part.
rem
rem Run this file once. To undo, see the Remove command printed at the end.

cd /d "%~dp0"
set TASKNAME=KIS_DataCollect

echo.
echo Registering scheduled task "%TASKNAME%" ...
echo.

schtasks /Create /F /TN "%TASKNAME%" /TR "\"%~dp0run_daemon_scheduled.bat\"" /SC DAILY /ST 08:50 /RI 60 /DU 0011:00

if %ERRORLEVEL%==0 (
  echo.
  echo [OK] Done. The collector will now start on its own every day at 08:50,
  echo      and retry hourly until 19:50 if the PC was off or asleep.
  echo.
  echo   Check  : schtasks /Query /TN "%TASKNAME%"
  echo   Run now: schtasks /Run   /TN "%TASKNAME%"
  echo   Remove : schtasks /Delete /TN "%TASKNAME%" /F
) else (
  echo.
  echo [FAIL] Registration failed.
  echo        Try again as Administrator: right-click this file
  echo        and choose "Run as administrator".
)

echo.
pause
