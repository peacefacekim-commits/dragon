@echo off
chcp 65001 >nul
REM 이 파일을 더블클릭하세요. (처음이라면 먼저 설치.bat 을 실행하세요)
cd /d "%~dp0"

if not exist config.json (
  echo config.json 이 없습니다. 먼저 설치.bat 을 실행해주세요.
  pause
  goto :끝
)

python autoplay.py
if errorlevel 1 (
  echo.
  echo 실행에 실패했습니다. 설치.bat 을 먼저 실행했는지 확인해주세요.
  echo.
  pause
)

:끝
