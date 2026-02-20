# StoryProof GCP Cloud Run 통합 배포 스크립트

param(
    [string]$ProjectId = "",
    [string]$Region = "asia-northeast3",
    [string]$ServiceName = "storyproof-backend"
)

# 1. gcloud 경로 찾기
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
    Write-Error "gcloud를 찾을 수 없습니다."
    exit 1
}

if ($ProjectId -eq "") {
    Write-Error "ProjectId를 입력해주세요."
    exit 1
}

# 2. 프로젝트 설정
Write-Host "🔧 프로젝트 설정: $ProjectId" -ForegroundColor Cyan
& $gcloud config set project $ProjectId

# 3. API 활성화
Write-Host "🔧 API 활성화 중..." -ForegroundColor Cyan
& $gcloud services enable run.googleapis.com
& $gcloud services enable cloudbuild.googleapis.com
& $gcloud services enable secretmanager.googleapis.com
& $gcloud services enable iam.googleapis.com

# 4. .env 파일 파싱 및 Secret 설정
Write-Host "🔐 .env 파일 처리 중..." -ForegroundColor Cyan
if (Test-Path ".env") {
    $content = Get-Content ".env"
    $envVars = @{}
    foreach ($line in $content) {
        if ($line -match "^([^#=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            $envVars[$key] = $value
        }
    }

    function Set-Secret ($name, $val) {
        if (-not $val) { return }
        Write-Host "   - $name 설정..." -ForegroundColor Gray
        # 시크릿 생성 시도 (이미 있으면 에러 무시)
        echo $val | & $gcloud secrets create $name --data-file=- --project $ProjectId 2>$null
        # 새 버전 추가
        echo $val | & $gcloud secrets versions add $name --data-file=- --project $ProjectId 2>$null
    }

    Set-Secret "google-api-key" $envVars["GOOGLE_API_KEY"]
    Set-Secret "pinecone-api-key" $envVars["PINECONE_API_KEY"]
    Set-Secret "database-url" $envVars["DATABASE_URL"]
    
    if ($envVars["SECRET_KEY"]) {
        Set-Secret "secret-key" $envVars["SECRET_KEY"]
    } else {
        $randKey = -join ((1..32) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
        Set-Secret "secret-key" $randKey
    }
}

# 5. 권한 부여 (Permission Denied 해결)
Write-Host "🔧 서비스 계정 권한 확인 및 부여..." -ForegroundColor Cyan
$projectNum = & $gcloud projects describe $ProjectId --format="value(projectNumber)"
$computeSa = "$projectNum-compute@developer.gserviceaccount.com"

Write-Host "   - 서비스 계정: $computeSa" -ForegroundColor Gray
& $gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$computeSa" --role="roles/storage.admin" 2>$null
& $gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$computeSa" --role="roles/run.admin" 2>$null
& $gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$computeSa" --role="roles/artifactregistry.admin" 2>$null
& $gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$computeSa" --role="roles/secretmanager.secretAccessor" 2>$null

# 6. 배포
Write-Host "🚀 배포 시작..." -ForegroundColor Cyan
& $gcloud run deploy $ServiceName `
    --source . `
    --region $Region `
    --platform managed `
    --allow-unauthenticated `
    --set-env-vars "PINECONE_INDEX_NAME=story-child-index-384,PINECONE_ENV=us-east-1,ALGORITHM=HS256,ACCESS_TOKEN_EXPIRE_MINUTES=30,WEB_CONCURRENCY=2" `
    --set-secrets "GOOGLE_API_KEY=google-api-key:latest,PINECONE_API_KEY=pinecone-api-key:latest,DATABASE_URL=database-url:latest,SECRET_KEY=secret-key:latest" `
    --memory 4Gi `
    --cpu 2 `
    --timeout 600 `
    --no-cpu-throttling `
    --max-instances 5 `
    --min-instances 0 `
    --port 8080
