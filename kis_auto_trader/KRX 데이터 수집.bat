@echo off
rem One-time KRX collection: dividends / PER / PBR (and market cap).
rem Double-click this file - no typing needed.
rem
rem (2026-09-19 rewritten) What this is for:
rem   Every price-derived signal has been tested and none of them beat the
rem   low-volatility selection already in use. The one signal still
rem   untested is fundamentals - dividend yield, PER, PBR - because they
rem   were never collected: krx_fund has only 29 of 1,813 stocks.
rem   That matters because SELECTION is the one dimension where an edge
rem   has actually shown up.
rem
rem   The earlier run stopped at 29 stocks and blamed the KRX login. The
rem   login was fine - the same account fetched 1,707 stocks of order
rem   flow. It aborted on 5 consecutive errors, which on a 25-minute run
rem   is just bad luck. That is fixed: each stock is retried once, and the
rem   abort threshold is much higher once anything has succeeded.
rem
rem What it does, in order:
rem   1. git pull                                          update scripts
rem   2. fetch_krx_extra.py --what fundamental --limit 3   format check ~1 min
rem      then STOPS so you can look at it
rem   3. fetch_krx_extra.py --what fundamental             ABOUT 10 HOURS
rem   4. fetch_krx_extra.py --what cap                     another ~10h, optional
rem   5. git commit + push
rem
rem Safe to close and re-run at any time: stocks already fetched are
rem skipped, so it picks up where it left off.
rem
rem Requires KRX_ID / KRX_PW environment variables (see fetch_krx_history.py).
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


echo.
echo ============================================================
echo  STEP 1/5  Updating scripts (git pull)
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
echo  STEP 2/5  Format check - 3 stocks only, about 1 minute
echo ============================================================
%PY% fetch_krx_extra.py --what fundamental --limit 3
if errorlevel 1 (
  echo.
  echo [FAIL] Format check failed. Copy the error above and send it to Claude.
  goto :end
)

echo.
echo ============================================================
echo  Format check passed. PER / PBR / DIV should show numbers above.
echo  The next step takes ABOUT 10 HOURS (20s per stock x 1,813).
echo  Best left running overnight. Close the window any time -
echo  progress is saved every 25 stocks and resumes where it stopped.
echo ============================================================
echo.
set /p GO="Start the full fundamentals collection? (y/n): "
if /i not "%GO%"=="y" (
  echo Stopped. Double-click this file again when ready.
  goto :end
)

echo.
echo ============================================================
echo  STEP 3/5  Dividends / PER / PBR - about 10 hours
echo ============================================================
%PY% fetch_krx_extra.py --what fundamental
if errorlevel 1 (
  echo.
  echo [WARN] Collection stopped early. Whatever was fetched is kept.
  echo        Re-run this file to continue from where it stopped.
)

echo.
echo ============================================================
echo  STEP 4/5  Market cap - another ~10 hours (optional)
echo ============================================================
echo  Not needed for the dividend / PER / PBR test, but it is the last
echo  KRX dataset still missing and you are already set up for it.
echo.
set /p GO2="Also collect market cap now? (y/n): "
if /i "%GO2%"=="y" (
  %PY% fetch_krx_extra.py --what cap
) else (
  echo Skipped. You can run this file again later for it.
)

echo.
echo ============================================================
echo  STEP 5/5  Saving to GitHub
echo ============================================================
git add data/
git commit -m "KRX fundamentals: dividend yield, PER, PBR"
echo  Pulling first - hours may have passed since STEP 1, and Claude
echo  may have pushed in the meantime. Without this the push is rejected.
git -c core.editor=true pull --no-edit
if errorlevel 1 (
  echo.
  echo [WARN] git pull failed. Your data is committed locally - nothing lost.
  echo        Tell Claude and stop here.
  goto :end
)
git push
if errorlevel 1 (
  echo.
  echo [WARN] Push failed, but the data is committed locally - nothing lost.
  echo        Try "git push" again later, or tell Claude.
  goto :end
)

echo.
echo ============================================================
echo  [OK] Done. Tell Claude how many stocks were collected.
echo ============================================================

:end
echo.
pause
