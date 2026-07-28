@echo off
chcp 65001 >nul
REM 통장 정리 도구 실행 - 이 파일을 더블클릭하세요.
cd /d "%~dp0.."

python -m passbook_ledger
if errorlevel 1 (
  echo.
  echo 실행에 실패했습니다.
  echo  - 파이썬이 설치되어 있는지 확인하세요 ^(명령 프롬프트에서 python --version^)
  echo  - 설치 시 "Add python.exe to PATH" 를 체크했는지 확인하세요
  echo  - OCR 자동 인식을 쓰려면 Tesseract OCR(한국어 데이터 포함)이 설치돼 있어야 합니다
  echo.
  pause
)
