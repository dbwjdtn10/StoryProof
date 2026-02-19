# 🚀 StoryProof GCP Cloud Run 빠른 배포 가이드

## 📌 3단계로 배포하기

### 1️⃣ GCP 프로젝트 확인

```powershell
# 현재 프로젝트 확인
gcloud projects list

# 프로젝트 설정
gcloud config set project YOUR-PROJECT-ID
```

### 2️⃣ Secret 설정

```powershell
# Secret 설정 스크립트 실행
.\setup-secrets.ps1 -ProjectId YOUR-PROJECT-ID
```

다음 정보를 입력하세요:
- **Google Gemini API Key**: [여기서 발급](https://aistudio.google.com/app/apikey)
- **Pinecone API Key**: [여기서 발급](https://www.pinecone.io/)
- **Database URL**: PostgreSQL 연결 문자열
- **Secret Key**: 자동 생성 (또는 직접 입력)

### 3️⃣ 배포 실행

```powershell
# 배포 스크립트 실행 (5-10분 소요)
.\deploy.ps1 -ProjectId YOUR-PROJECT-ID
```

배포가 완료되면 서비스 URL이 표시됩니다:
```
https://storyproof-backend-xxxxx-an.a.run.app
```

---

## ✅ 배포 확인

```powershell
# API 테스트
curl https://storyproof-backend-xxxxx-an.a.run.app/health

# 로그 확인
gcloud run services logs read storyproof-backend --region asia-northeast3
```

---

## 🔧 수동 배포 (스크립트 없이)

### 1. Secret 생성

```powershell
echo "YOUR-GOOGLE-API-KEY" | gcloud secrets create google-api-key --data-file=-
echo "YOUR-PINECONE-API-KEY" | gcloud secrets create pinecone-api-key --data-file=-
echo "postgresql://user:pass@host:5432/db" | gcloud secrets create database-url --data-file=-
echo "YOUR-SECRET-KEY" | gcloud secrets create secret-key --data-file=-
```

### 2. Cloud Run 배포

```powershell
gcloud run deploy storyproof-backend `
  --source . `
  --region asia-northeast3 `
  --platform managed `
  --allow-unauthenticated `
  --set-env-vars "PINECONE_INDEX_NAME=story-child-index-384,PINECONE_ENV=us-east-1" `
  --set-secrets "GOOGLE_API_KEY=google-api-key:latest,PINECONE_API_KEY=pinecone-api-key:latest,DATABASE_URL=database-url:latest,SECRET_KEY=secret-key:latest" `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300
```

---

## 📚 추가 문서

자세한 내용은 [deployment_guide.md](./deployment_guide.md)를 참고하세요.

### 주요 내용
- 배포 아키텍처 설명
- 데이터베이스 연결 (Cloud SQL)
- Frontend 배포 (Firebase Hosting)
- 트러블슈팅 가이드
- 비용 최적화 팁

---

## ❓ 자주 묻는 질문

### Q1. 비용이 얼마나 나오나요?
- **무료 티어**: 월 200만 요청까지 무료
- **최소 인스턴스 0**: 사용하지 않을 때 0원
- **예상 비용**: 소규모 프로젝트는 월 $5 이하

### Q2. 데이터베이스는 어떻게 연결하나요?
- **Cloud SQL**: GCP 관리형 PostgreSQL 사용
- **외부 DB**: Supabase, Neon 등 사용 가능
- 자세한 내용은 [deployment_guide.md](./deployment_guide.md#데이터베이스-연결) 참고

### Q3. Frontend는 어떻게 배포하나요?
- **권장**: Firebase Hosting 또는 Vercel
- **대안**: Cloud Storage + CDN
- 자세한 내용은 [deployment_guide.md](./deployment_guide.md#frontend-배포-firebase-hosting) 참고

### Q4. 배포 후 수정사항이 생기면?
```powershell
# 코드 수정 후 재배포
.\deploy.ps1 -ProjectId YOUR-PROJECT-ID
```

### Q5. 로컬에서 Docker 테스트하려면?
```powershell
# Docker 이미지 빌드
docker build -t storyproof-backend .

# 로컬 실행
docker run -p 8080:8080 --env-file .env storyproof-backend

# 테스트
curl http://localhost:8080/health
```

---

## 🆘 문제 해결

### 배포 실패 시
1. 로그 확인: `gcloud run services logs read storyproof-backend`
2. Secret 확인: `gcloud secrets list`
3. API 활성화 확인: `gcloud services list --enabled`

### 더 많은 도움이 필요하면
- [deployment_guide.md - 트러블슈팅](./deployment_guide.md#트러블슈팅) 참고
- [Cloud Run 공식 문서](https://cloud.google.com/run/docs)
