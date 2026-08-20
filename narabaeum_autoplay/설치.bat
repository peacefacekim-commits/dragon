@echo off
chcp 65001 >nul
REM 처음 한 번만 실행하세요. 필요한 프로그램을 설치합니다.
cd /d "%~dp0"

echo 필요한 패키지를 설치합니다...
python -m pip install -r requirements.txt
if errorlevel 1 goto :실패

echo 브라우저(Chromium)를 설치합니다...
python -m playwright install chromium
if errorlevel 1 goto :실패

if not exist config.json (
  copy config.example.json config.json >nul
  echo.
  echo config.json 을 만들었습니다. 메모장으로 열어서
  echo next_lecture_selector 등 값을 채워주세요.
)

echo.
echo 설치가 끝났습니다. 이제 실행.bat 을 실행하세요.
pause
goto :끝

:실패
echo.
echo 설치에 실패했습니다.
echo  - 파이썬이 설치되어 있는지 확인하세요 ^(명령 프롬프트에서 python --version^)
echo  - 설치 시 "Add python.exe to PATH" 를 체크했는지 확인하세요
echo.
pause

:끝
