@echo off
rem One-click scoring of the frozen bad-day gate. Double-click - no typing.
rem
rem What it does:
rem   1. git pull                       (get the latest scripts)
rem   2. paper_trade.py --record        (log today's picks + gate verdict)
rem   3. paper_trade.py --settle        (fill in matured rounds' returns)
rem   4. paper_trade.py --score         (report whether the gate is working)
rem   5. git commit + push              (keep the scoring log)
rem
rem The daily collector (collect_daily.py) already runs steps 2-3 every day,
rem so this file is for when you just want to LOOK at the score.
rem
rem It never places an order. It reads CSV files and writes CSV files.
rem
rem Do NOT run --freeze again. The gate coefficients in
rem data\gate_frozen.json were fixed on 2026-09-17. Refitting them to newer
rem data turns forward validation back into a backtest, which is the whole
rem thing this is trying to avoid.
rem
rem ASCII-only on purpose: Korean text in .bat files turns to mojibake
rem depending on the console code page.

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
echo === 1/4  git pull ===
git -c core.editor=true pull --no-edit

echo.
echo === 2/4  record today's round ===
%PY% paper_trade.py --record

echo.
echo === 3/4  settle matured rounds ===
%PY% paper_trade.py --settle

echo.
echo === 4/4  score the frozen gate ===
%PY% paper_trade.py --score

echo.
echo === saving the scoring log ===
git add data/paper_trades_*.csv data/gate_frozen.json
git commit -m "paper trade log update"
rem Pull before pushing. Claude may have pushed since the pull at step 1,
rem and then the push is rejected with "fetch first".
git -c core.editor=true pull --no-edit
git push

echo.
echo Done. Press any key to close.
pause >nul
