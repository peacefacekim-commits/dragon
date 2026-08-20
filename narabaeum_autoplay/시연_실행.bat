@echo off
chcp 65001 >nul
REM 실제 사이트 없이, 모의 강의 화면으로 자동 전환을 보여주는 시연용 실행 파일입니다.
REM 먼저 설치.bat 을 한 번 실행해두어야 합니다.
cd /d "%~dp0"

python autoplay.py --config demo\demo_config.json --start-file demo\lecture1.html
if errorlevel 1 (
  echo.
  echo 실행에 실패했습니다. 설치.bat 을 먼저 실행했는지 확인해주세요.
  echo.
  pause
)
