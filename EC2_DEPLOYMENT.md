# StoryProof AWS EC2 배포 가이드

이 문서는 StoryProof 애플리케이션(FastAPI + React)을 AWS EC2(Ubuntu 22.04 LTS)에 배포하는 방법을 안내합니다.

## 📋 사전 준비 사항

1.  **AWS 계정**: AWS 콘솔 접근 권한.
2.  **API 키**: Google Gemini API 키, Pinecone API 키.
3.  **도메인 (선택 사항)**: HTTPS 적용을 위해 필요합니다. (이 가이드는 IP 기반 접속을 우선 다룹니다.)
4.  **SSH 클라이언트**: 터미널 (Mac/Linux) 또는 PowerShell/Putty (Windows).

---

## 🚀 1단계: EC2 인스턴스 생성

1.  **AWS Console 로그인** 후 **EC2** 서비스로 이동합니다.
2.  **인스턴스 시작 (Launch Instances)** 클릭.
3.  **이름 및 태그**: `StoryProof-Server` 등 식별 가능한 이름 입력.
4.  **OS 이미지 (AMI)**: **Ubuntu Server 22.04 LTS (HVM)** 선택 (Architecture: 64-bit (x86)).
5.  **인스턴스 유형**: **`t3.small`** (2GB RAM).
    *   Reranker 비활성화(`ENABLE_RERANKER=False`) + 2GB Swap 자동 구성으로 t3.small에서 운영 가능합니다.
    *   트래픽이 늘거나 분석 작업이 잦아지면 `t3.medium` (4GB) 업그레이드를 권장합니다.
6.  **키 페어 (Key Pair)**: 새 키 페어 생성 (`storyproof-key` 등) 후 `.pem` 파일 다운로드.
7.  **네트워크 설정 (Security Group)**:
    *   **SSH (22)**: 내 IP에서만 허용 (보안 권장).
    *   **HTTP (80)**: 위치 무관 (0.0.0.0/0).
    *   **HTTPS (443)**: 위치 무관 (0.0.0.0/0).
    *   **주의**: "규칙 중복" 에러가 뜨면, 동일한 포트(80, 443 등)에 대한 규칙이 이미 리스트에 있는지 확인하고 중복된 줄을 삭제(X 버튼)하세요.
8.  **스토리지**: 기본 8GB → **20GB 이상**으로 증설 (Python 패키지, ML 모델, 로그 공간 필요).
9.  **인스턴스 시작** 클릭 후 **퍼블릭 IPv4 주소** 메모.

---

## 💻 2단계: 서버 접속 및 코드 설정

1.  다운로드 받은 키 페어 파일(`storyproof-key.pem`)의 권한을 설정합니다.
    (Windows PowerShell 예시)
    ```powershell
    icacls.exe storyproof-key.pem /reset
    icacls.exe storyproof-key.pem /grant:r "$($env:USERNAME):(R)"
    icacls.exe storyproof-key.pem /inheritance:r
    ```

2.  SSH로 서버에 접속합니다. (`YOUR_SERVER_IP`는 EC2의 퍼블릭 IP)
    ```bash
    ssh -i "storyproof-key.pem" ubuntu@YOUR_SERVER_IP
    ```

3.  **Git Clone & 코드 준비**:
    *   Github 저장소에서 코드를 가져옵니다. (Private 저장소인 경우 HTTPS 토큰 방식이나 SSH 키 등록 필요)
    ```bash
    git clone https://github.com/dbwjdtn10/StoryProof.git
    cd StoryProof
    ```

4.  **환경 변수 설정 (두 가지 방법 중 선택)**:
    *   **방법 A (추천): 로컬에서 파일 복사** (새 터미널 창을 열어서 실행)
        ```powershell
        scp -i "storyproof-key.pem" .env ubuntu@YOUR_SERVER_IP:~/StoryProof/.env
        ```
    *   **방법 B: 서버에서 직접 생성** (SSH 접속한 터미널에서 실행)
        ```bash
        cd ~/StoryProof
        nano .env
        # (내용 붙여넣기 후 Ctrl+O -> Enter -> Ctrl+X)
        ```

    *   **필수 .env 항목**:
        ```
        GOOGLE_API_KEY=실제_Gemini_API_키
        PINECONE_API_KEY=실제_Pinecone_API_키
        PINECONE_INDEX_NAME=story-child-index-384
        PINECONE_ENV=us-east-1

        # setup_ec2.sh가 생성하는 DB 계정과 반드시 일치해야 함
        DATABASE_URL=postgresql://storyproof:storyproof_password@localhost/storyproof

        # openssl rand -hex 32 로 생성
        SECRET_KEY=랜덤_32바이트_키

        # EC2 퍼블릭 IP로 교체
        CORS_ORIGINS=["http://YOUR_SERVER_IP"]

        ENVIRONMENT=production
        ```
    *   `SECRET_KEY` 생성: 서버에서 `openssl rand -hex 32` 실행 후 복사.

---

## 🛠 3단계: 설치 스크립트 실행

`scripts/setup_ec2.sh` 스크립트가 다음 작업을 자동으로 수행합니다:

*   시스템 패키지 업데이트
*   **Swap 파일 2GB 생성 및 영구 마운트** (t3.small 메모리 보완)
*   Python 3.10+, Redis, PostgreSQL, Nginx, Supervisor, Node.js 설치
*   PostgreSQL 데이터베이스 및 사용자 생성
*   Python 가상환경 생성 및 의존성 설치 (약 10~20분 소요)
*   Nginx 리버스 프록시 및 Supervisor 프로세스 설정 적용

```bash
chmod +x scripts/setup_ec2.sh
./scripts/setup_ec2.sh
```

설치 완료 후 서비스가 자동으로 시작됩니다.

> **참고**: 임베딩 모델(`multilingual-e5-small-ko`) 첫 로딩에 30초~1분 정도 소요됩니다.
> 설치 직후 접속이 안 되더라도 잠시 기다린 뒤 다시 시도하세요.

---

## 🔄 4단계: 코드 업데이트 배포

코드를 수정한 뒤 서버에 반영할 때 사용합니다.

```bash
chmod +x scripts/deploy_ec2.sh
./scripts/deploy_ec2.sh
```

이 스크립트는 git pull → pip install → DB 마이그레이션 → 프론트엔드 빌드 → 서비스 재시작을 순서대로 수행합니다.

---

## 🔍 상태 확인 및 문제 해결

*   **서비스 상태 확인**:
    ```bash
    sudo supervisorctl status
    ```
    `storyproof-backend`, `storyproof-celery` 모두 `RUNNING` 상태여야 합니다.

*   **로그 확인**:
    ```bash
    # 백엔드 에러 로그
    tail -f /var/log/storyproof/backend.err.log

    # Celery 에러 로그
    tail -f /var/log/storyproof/celery.err.log

    # Nginx 에러 로그
    tail -f /var/log/nginx/error.log
    ```

*   **메모리 사용량 확인** (t3.small 운영 시 주기적으로 체크 권장):
    ```bash
    free -h
    ```

*   **서비스 재시작**:
    ```bash
    sudo supervisorctl restart storyproof-backend
    sudo supervisorctl restart storyproof-celery
    sudo systemctl restart nginx
    ```

---

## 🌐 접속 확인

브라우저에서 `http://YOUR_SERVER_IP` 로 접속하여 StoryProof가 정상 동작하는지 확인합니다.
