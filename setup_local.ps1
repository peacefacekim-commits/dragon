# Windows PowerShell 자동 설정 스크립트
# 사용방법: PowerShell에서 `.\setup_local.ps1` 실행

param(
    [string]$KIS_APP_KEY = "",
    [string]$KIS_APP_SECRET = ""
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "KIS Auto Trader 로컬 자동 설정" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1단계: Python 확인
Write-Host "1️⃣  Python 확인 중..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3") {
    Write-Host "✅ Python 설치됨: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "❌ Python 설치 필요 (https://python.org)" -ForegroundColor Red
    exit 1
}

# 2단계: 라이브러리 설치
Write-Host ""
Write-Host "2️⃣  라이브러리 설치 중..." -ForegroundColor Yellow
pip install -r requirements.txt -q
if ($?) {
    Write-Host "✅ 라이브러리 설치 완료" -ForegroundColor Green
} else {
    Write-Host "❌ 라이브러리 설치 실패" -ForegroundColor Red
    exit 1
}

# 3단계: .env 파일 생성
Write-Host ""
Write-Host "3️⃣  .env 파일 설정..." -ForegroundColor Yellow

if ([string]::IsNullOrEmpty($KIS_APP_KEY)) {
    $KIS_APP_KEY = Read-Host "KIS API Key 입력"
}
if ([string]::IsNullOrEmpty($KIS_APP_SECRET)) {
    $KIS_APP_SECRET = Read-Host "KIS API Secret 입력"
}

$envContent = @"
KIS_APP_KEY=$KIS_APP_KEY
KIS_APP_SECRET=$KIS_APP_SECRET
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
"@

$envPath = ".env"
$envContent | Out-File -FilePath $envPath -Encoding UTF8
Write-Host "✅ .env 파일 생성됨: $((Get-Item $envPath).FullName)" -ForegroundColor Green

# 4단계: 로그 폴더 생성
Write-Host ""
Write-Host "4️⃣  로그 폴더 생성..." -ForegroundColor Yellow
if (!(Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
    Write-Host "✅ logs 폴더 생성됨" -ForegroundColor Green
} else {
    Write-Host "✅ logs 폴더 이미 존재" -ForegroundColor Green
}

# 5단계: 배치 파일 생성
Write-Host ""
Write-Host "5️⃣  배치 파일 생성..." -ForegroundColor Yellow

$scriptDir = (Get-Item -Path ".").FullName
$batchContent = @"
@echo off
cd /d "$scriptDir"
python collect_daily_prices.py >> logs\prices.log 2>&1
python collect_paper_signals.py >> logs\signals.log 2>&1
"@

$batchPath = "run_collect.bat"
$batchContent | Out-File -FilePath $batchPath -Encoding ASCII
Write-Host "✅ 배치 파일 생성됨: $((Get-Item $batchPath).FullName)" -ForegroundColor Green

# 6단계: 테스트 실행
Write-Host ""
Write-Host "6️⃣  테스트 실행 중..." -ForegroundColor Yellow
Write-Host ""

$testResult = python collect_daily_prices.py 2>&1
Write-Host $testResult

if ($testResult -match "✅") {
    Write-Host ""
    Write-Host "✅ 테스트 성공!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "⚠️  테스트 실행했으나 결과 확인 필요" -ForegroundColor Yellow
}

# 7단계: 작업 스케줄러 설정
Write-Host ""
Write-Host "7️⃣  작업 스케줄러 설정..." -ForegroundColor Yellow

$taskName = "KIS 가격 수집"
$taskPath = "\$taskName"
$batchFullPath = "$scriptDir\$batchPath"

# 기존 작업 제거
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "⏭️  기존 작업 제거됨" -ForegroundColor Yellow
}

# 새 작업 생성
$trigger = New-ScheduledTaskTrigger -Daily -At 17:00
$action = New-ScheduledTaskAction -Execute $batchFullPath -WorkingDirectory $scriptDir
$principal = New-ScheduledTaskPrincipal -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -RunOnlyIfNetworkAvailable

Register-ScheduledTask -TaskName $taskName `
    -Trigger $trigger `
    -Action $action `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

Write-Host "✅ 작업 스케줄러 설정 완료" -ForegroundColor Green
Write-Host "   - 매일 17:00에 자동 실행" -ForegroundColor Green

# 최종 확인
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ 자동 설정 완료!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 설정 내용:" -ForegroundColor Green
Write-Host "   1. Python 라이브러리: 설치됨" -ForegroundColor Green
Write-Host "   2. .env 파일: 생성됨" -ForegroundColor Green
Write-Host "   3. 배치 파일: $batchPath" -ForegroundColor Green
Write-Host "   4. 작업 스케줄러: $taskName (매일 17:00)" -ForegroundColor Green
Write-Host "   5. 로그 폴더: logs/" -ForegroundColor Green
Write-Host ""
Write-Host "🎯 다음 단계:" -ForegroundColor Yellow
Write-Host "   - 매일 17:00에 자동 실행됨" -ForegroundColor Yellow
Write-Host "   - logs/prices.log 에서 실행 로그 확인 가능" -ForegroundColor Yellow
Write-Host "   - 수동 실행: python collect_daily_prices.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "❓ 문제 발생 시:" -ForegroundColor Red
Write-Host "   - logs/prices.log 확인" -ForegroundColor Red
Write-Host "   - .env 파일의 API 키 확인" -ForegroundColor Red
Write-Host ""
