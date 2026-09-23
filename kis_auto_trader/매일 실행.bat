@echo off
rem One-click daily run. Double-click this file - no typing needed.
rem
rem (2026-09-19) This replaces four separate files:
rem     US index collection / futures collection / strategy data update /
rem     today's order sheet
rem
rem Why one file: the steps DEPEND ON EACH OTHER and the order matters.
rem   market_indicators (inside collect_daily.py) reads the US data through
rem   us_align and reads krx_panel. So the US and Korean data must be
rem   fetched FIRST, or that day's indicator row is built from yesterday's
rem   US numbers. Run as separate files, the order was whatever you
rem   happened to click.
rem
rem Note: daemon.py already runs these same steps by itself after the
rem market closes. This file is for running them NOW - when the PC was
rem off, or you just want today's order sheet immediately. Running it
rem twice in a day is harmless; every step resumes from what is stored.
rem
rem What it does, in order:
rem   1. git pull                       update scripts
rem   2. fetch_intraday.py              10-MINUTE BARS (today only) ~5 min
rem   3. fetch_us_market.py             US indices + VIX + rates   ~1 min
rem   4. fetch_us_futures.py            US futures (ES, NQ)        ~2 min
rem   5. fetch_krx_history.py --update  KOREAN DAILY BARS          ~15-25 min
rem                                     (this is the one the strategy reads)
rem   6. collect_daily.py               indicators + paper log     ~3 min
rem   7. git commit + push              keep the data
rem   8. plan_2m.py                     today's order sheet
rem   9. monitor.py                     strategy health check     ~2 min                     today's order sheet
rem
rem A failing step only warns - it does not stop the rest. A yfinance
rem hiccup must not cost you the Korean daily bars.
rem
rem Step 4 needs KRX_ID / KRX_PW environment variables. Without them it
rem is skipped with a message (see fetch_krx_history.py for setup).
rem
rem NOT included on purpose:
rem   KRX fundamentals bat   70-minute one-time backfill
rem   daemon start bat       daemon.py stays running - would block the rest
rem   scheduler register bat one-time, needs administrator
rem   gate scoring bat       a report you read, not collection
rem
rem ASCII-only on purpose: Korean text in .bat files turns to mojibake
rem depending on the console code page.

chcp 65001 > nul
cd /d "%~dp0"
set PY="C:\dev_python\python.exe"
if not exist %PY% set PY=python

rem ---- STEP 0: an unfinished merge blocks every later git command ----
rem (2026-09-21) A bare "git pull" opens an editor for the merge message.
rem Closing that editor without saving leaves .git\MERGE_HEAD behind, and
rem then EVERY later "git pull" fails with:
rem     error: You have not concluded your merge (MERGE_HEAD exists).
rem That silently blocked data uploads for days - the overnight KRX
rem fundamentals collection sat on the PC unable to reach GitHub.
rem This finishes a clean merge by itself and stops loudly only when a
rem human decision is actually needed.
echo.
echo ============================================================
echo  STEP 0  Unfinished merge check
echo ============================================================
if not exist ".git\MERGE_HEAD" goto :nomerge
echo  An earlier merge was left unfinished. Checking for conflicts...
set CONFSIZE=0
git diff --name-only --diff-filter=U > "%TEMP%\kis_conflicts.txt" 2>nul
for %%A in ("%TEMP%\kis_conflicts.txt") do set CONFSIZE=%%~zA
if not "%CONFSIZE%"=="0" (
  echo.
  echo  [STOP] This merge has conflicts that need a decision:
  type "%TEMP%\kis_conflicts.txt"
  echo.
  echo  Nothing was changed and no data was lost.
  echo  Show the list above to Claude.
  pause
  exit /b 1
)
git -c core.editor=true commit --no-edit
if errorlevel 1 (
  echo.
  echo  [STOP] Could not finish the merge. Nothing was changed.
  echo  Show this screen to Claude.
  pause
  exit /b 1
)
echo  [OK] Unfinished merge completed. Continuing.
:nomerge

set FAILED=

echo.
echo ============================================================
echo  STEP 1/8  Updating scripts (git pull)
echo ============================================================
git -c core.editor=true pull --no-edit
if errorlevel 1 (
  echo.
  echo [FAIL] git pull failed. If it mentions local changes, run:
  echo          git stash
  echo        then double-click this file again.
  goto :end
)

echo.
echo ============================================================
echo  STEP 2/8  10-MINUTE BARS for today          (about 5 min)
echo ============================================================
echo  IMPORTANT: the KIS intraday API only serves TODAY. A day you
echo  miss is gone forever - there is no way to backfill it later.
echo  Run this every trading day after the close.
echo.
echo  NOTE: run this AFTER 15:30. Before the close the API returns
echo  empty bars (zero volume) stamped with TODAY's date. Those are
echo  skipped now, but you still have to re-run after the close.
echo.
%PY% fetch_intraday.py
if errorlevel 1 (
  echo [WARN] No 10-minute bars were saved. If it says the bars were
  echo        empty, the market has not closed yet - run this again
  echo        after 15:30. TODAY IS LOST if you never do.
  echo        To inspect: python fetch_intraday.py --check
  set FAILED=%FAILED% min10
)

echo.
echo ============================================================
echo  STEP 3/8  US indices, VIX, 10-year rate       (about 1 min)
echo ============================================================
%PY% fetch_us_market.py
if errorlevel 1 (
  echo [WARN] US index collection failed. Continuing.
  set FAILED=%FAILED% us-index
)

echo.
echo ============================================================
echo  STEP 4/8  US futures ES / NQ                  (about 2 min)
echo ============================================================
%PY% fetch_us_futures.py
if errorlevel 1 (
  echo [WARN] Futures collection failed. Continuing.
  set FAILED=%FAILED% us-futures
)

echo.
echo ============================================================
echo  STEP 5/8  Korean daily bars - missing days  (15-25 min)
echo ============================================================
echo  This is the panel the strategy actually reads (krx_panel).
echo  About 1,744 stocks, 0.4s apart. Leave it running.
echo  Close the window any time - it resumes from the last stored day.
echo.
%PY% fetch_krx_history.py --update
if errorlevel 1 (
  echo [WARN] KRX update failed - most often KRX_ID / KRX_PW is not set.
  echo        Partial data is kept. Continuing.
  set FAILED=%FAILED% krx-panel
)

echo.
echo ============================================================
echo  STEP 6/8  Indicators + paper-trade log        (about 3 min)
echo ============================================================
%PY% collect_daily.py
if errorlevel 1 (
  echo [WARN] collect_daily.py reported a problem. Continuing.
  set FAILED=%FAILED% daily-collect
)

echo.
echo ============================================================
echo  STEP 7/8  Saving to GitHub
echo ============================================================
git add data/
git commit -m "daily data: us market, futures, krx panel, indicators"
echo  Pulling first - time has passed since STEP 1 and Claude may have
echo  pushed in the meantime. Without this the push is rejected.
git -c core.editor=true pull --no-edit
if errorlevel 1 (
  echo [WARN] git pull failed. Data is committed locally - nothing lost.
  set FAILED=%FAILED% pull
  goto :skippush
)
git push
if errorlevel 1 (
  echo [WARN] Push failed, but the data is committed locally - nothing lost.
  echo        Try "git push" again later, or tell Claude.
  set FAILED=%FAILED% push
)
:skippush

echo.
echo ============================================================
echo  STEP 8/9  Today's order sheet
echo ============================================================
%PY% plan_2m.py

echo.
echo ============================================================
echo  STEP 9/9  Strategy health check        (about 2 min)
echo ============================================================
echo  This is the part a person cannot do daily: it recomputes the
echo  three numbers that say whether the low-volatility edge is
echo  still intact (up/down day ratio, down-day capture, up-day
echo  follow). It places no orders - it only reports.
echo.
%PY% monitor.py
if errorlevel 1 (
  echo [WARN] Health check failed. Nothing was traded - safe to ignore
  echo        for today, but tell Claude if it keeps failing.
  set FAILED=%FAILED% health
)

echo.
echo ============================================================
if "%FAILED%"=="" (
  echo  [OK] All steps finished.
) else (
  echo  [PARTIAL] Finished, but these steps failed:%FAILED%
  echo            Re-running this file retries only what is missing.
)
echo ============================================================

:end
echo.
pause
