# GCP Secret Manager 설정 스크립트
# 환경 변수를 Secret Manager에 등록

param(
    [string]$ProjectId = ""
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GCP Secret Manager 설정" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# gcloud 경로 찾기 함수
function Get-GcloudPath {
    $potentialPaths = @(
        "gcloud",
        "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$env:ProgramFiles(x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$env:ProgramFiles\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    )

    foreach ($path in $potentialPaths) {
        if (Get-Command $path -ErrorAction SilentlyContinue) {
            return $path
        }
        if (Test-Path $path) {
            return $path
        }
    }
    return $null
}

$gcloud = Get-GcloudPath

if (-not $gcloud) {
    Write-Host "❌ gcloud를 찾을 수 없습니다. Google Cloud SDK가 설치되어 있는지 확인해주세요." -ForegroundColor Red
    exit 1
}

Write-Host "✅ gcloud 경로: $gcloud" -ForegroundColor Green
Write-Host ""

# 프로젝트 ID 확인
if ($ProjectId -eq "") {
    Write-Host "❌ 프로젝트 ID를 입력해주세요." -ForegroundColor Red
    Write-Host "사용법: .\setup-secrets.ps1 -ProjectId your-project-id" -ForegroundColor Yellow
    exit 1
}

# 프로젝트 설정
& $gcloud config set project $ProjectId

# Secret Manager API 활성화
Write-Host "🔧 Secret Manager API 활성화 중..." -ForegroundColor Yellow
& $gcloud services enable secretmanager.googleapis.com

Write-Host ""
Write-Host "📝 환경 변수를 입력해주세요." -ForegroundColor Green
Write-Host "   (입력 후 Enter를 누르세요. 빈 값은 건너뜁니다.)" -ForegroundColor Cyan
Write-Host ""

# 1. Google API Key
Write-Host "1️⃣  Google Gemini API Key:" -ForegroundColor Yellow
$googleApiKey = Read-Host "   "
if ($googleApiKey -ne "") {
    echo $googleApiKey | & $gcloud secrets create google-api-key --data-file=- 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ google-api-key 생성 완료" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  이미 존재하거나 생성 실패. 업데이트 시도 중..." -ForegroundColor Yellow
        echo $googleApiKey | & $gcloud secrets versions add google-api-key --data-file=-
    }
}

# 2. Pinecone API Key
Write-Host ""
Write-Host "2️⃣  Pinecone API Key:" -ForegroundColor Yellow
$pineconeApiKey = Read-Host "   "
if ($pineconeApiKey -ne "") {
    echo $pineconeApiKey | & $gcloud secrets create pinecone-api-key --data-file=- 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ pinecone-api-key 생성 완료" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  이미 존재하거나 생성 실패. 업데이트 시도 중..." -ForegroundColor Yellow
        echo $pineconeApiKey | & $gcloud secrets versions add pinecone-api-key --data-file=-
    }
}

# 3. Database URL
Write-Host ""
Write-Host "3️⃣  Database URL:" -ForegroundColor Yellow
Write-Host "   예시: postgresql://user:password@host:5432/database" -ForegroundColor Cyan
$databaseUrl = Read-Host "   "
if ($databaseUrl -ne "") {
    echo $databaseUrl | & $gcloud secrets create database-url --data-file=- 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ database-url 생성 완료" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  이미 존재하거나 생성 실패. 업데이트 시도 중..." -ForegroundColor Yellow
        echo $databaseUrl | & $gcloud secrets versions add database-url --data-file=-
    }
}

# 4. Secret Key (JWT)
Write-Host ""
Write-Host "4️⃣  Secret Key (JWT 토큰용):" -ForegroundColor Yellow
Write-Host "   비워두면 자동 생성됩니다." -ForegroundColor Cyan
$secretKey = Read-Host "   "
if ($secretKey -eq "") {
    # 랜덤 키 생성 (32바이트 hex)
    $secretKey = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
    Write-Host "   🔑 자동 생성된 Secret Key: $secretKey" -ForegroundColor Cyan
}
echo $secretKey | & $gcloud secrets create secret-key --data-file=- 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ secret-key 생성 완료" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  이미 존재하거나 생성 실패. 업데이트 시도 중..." -ForegroundColor Yellow
    echo $secretKey | & $gcloud secrets versions add secret-key --data-file=-
}

# 완료
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ Secret 설정 완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "생성된 Secret 목록:" -ForegroundColor Yellow
& $gcloud secrets list

Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Cyan
Write-Host "  .\deploy.ps1 -ProjectId $ProjectId" -ForegroundColor White
