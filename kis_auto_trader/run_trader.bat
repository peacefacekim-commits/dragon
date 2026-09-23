@echo off
cd /d "%~dp0"
echo. >> logs\run_console.log
echo [%date% %time%] run_trader.bat 시작 >> logs\run_console.log
rem -u : 출력 버퍼링 끄기. 중간에 비정상 종료돼도 그때까지의 로그가 남는다.
"C:\dev_python\python.exe" -u main.py >> logs\run_console.log 2>&1
echo [%date% %time%] main.py 종료, 종료코드=%ERRORLEVEL% >> logs\run_console.log
