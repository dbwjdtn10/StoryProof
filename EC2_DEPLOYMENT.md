# StoryProof AWS EC2 배포 가이드

이 문서는 StoryProof 애플리케이션(FastAPI + React)을 AWS EC2(Ubuntu 22.04 LTS)에 배포하는 방법을 안내합니다.

## 📋 사전 준비 사항

1.  **AWS 계정**: AWS 콘솔 접근 권한.
2.  **도메인 (선택 사항)**: HTTPS 적용을 위해 필요합니다. (이 가이드는 IP 기반 접속을 우선 다룹니다.)
3.  **SSH 클라이언트**: 터미널 (Mac/Linux) 또는 PowerShell/Putty (Windows).

---

## 🚀 1단계: EC2 인스턴스 생성

1.  **AWS Console 로그인** 후 **EC2** 서비스로 이동합니다.
2.  **인스턴스 시작 (Launch Instances)** 클릭.
3.  **이름 및 태그**: `StoryProof-Server` 등 식별 가능한 이름 입력.
4.  **OS 이미지 (AMI)**: **Ubuntu Server 22.04 LTS (HVM)** 선택 (Architecture: 64-bit (x86)).
5.  **인스턴스 유형**: `t3.small` 이상 권장 (AI 모델 구동 시 메모리 필요).
    *   *참고: 프리 티어(`t2.micro`)는 메모리 부족으로 빌드나 서버 구동이 실패할 수 있습니다.*
6.  **키 페어 (Key Pair)**: 새 키 페어 생성 (`storyproof-key` 등) 후 `.pem` 파일 다운로드.
7.  **네트워크 설정 (Security Group)**:
    *   **SSH (22)**: 내 IP에서만 허용 (보안 권장).
    *   **HTTP (80)**: 위치 무관 (0.0.0.0/0).
    *   **HTTPS (443)**: 위치 무관 (0.0.0.0/0).
    *   **주의**: "규칙 중복" 에러가 뜨면, 동일한 포트(80, 443 등)에 대한 규칙이 이미 리스트에 있는지 확인하고 중복된 줄을 삭제(X 버튼)하세요.
8.  **스토리지**: 기본 8GB -> **20GB 이상**으로 증설 권장 (Docker, 라이브러리 등 공간 필요).
9.  **인스턴스 시작** 클릭.

---

## 💻 2단계: 서버 접속 및 코드 설정

1.  다운로드 받은 키 페어 파일(`storyproof-key.pem`)의 권한을 설정합니다 (Linux/Mac). Windows는 생략 가능하거나 속성에서 보안 설정.
    (Windows PowerShell 예시)
    ```powershell
    icacls.exe storyproof-key.pem /reset
    icacls.exe storyproof-key.pem /grant:r "$($env:USERNAME):(R)"
    icacls.exe storyproof-key.pem /inheritance:r
    ```
2.  SSH로 서버에 접속합니다. (`YOUR_SERVER_IP`는 EC2의 퍼블릭 IP)
    ```bash
    ssh -i "path/to/storyproof-key.pem" ubuntu@YOUR_SERVER_IP
    ```

3.  **Git Clone & 코드 준비**:
    *   Github 저장소에서 코드를 가져옵니다. (Private 저장소인 경우 HTTPS 토큰 방식이나 SSH 키 등록 필요)
    ```bash
    git clone https://github.com/dbwjdtn10/StoryProof.git
    cd StoryProof
    ```

4.  **환경 변수 설정**:
    *   로컬 개발 환경의 `.env` 파일을 서버로 복사하거나 새로 생성합니다.
    ```bash
    nano .env
    ```
    *   내용을 붙여넣고 `Ctrl+O` (저장), `Enter`, `Ctrl+X` (종료).
    *   **중요**: `DATABASE_URL`은 로컬 DB를 쓸 경우 `postgresql://storyproof:storyproof_password@localhost/storyproof` 로 설정될 것입니다 (스크립트가 자동 생성). 외부 DB(RDS)를 쓴다면 해당 URL 입력.

---

## 🛠 3단계: 자동지 설치 스크립트 실행

`scripts/setup_ec2.sh` 스크립트는 다음 작업을 자동으로 수행합니다:
*   시스템 패키지 업데이트
*   Python 3.10+, Redis, PostgreSQL, Nginx, Supervisor 설치
*   PostgreSQL 데이터베이스 및 사용자 생성
*   Python 가상환경 생성 및 의존성 설치
*   Nginx 및 Supervisor 설정 파일 생성 및 적용

```bash
# 스크립트 실행 권한 부여
chmod +x scripts/setup_ec2.sh

# 설치 스크립트 실행
./scripts/setup_ec2.sh
```

설치가 완료되면 서버가 자동으로 시작됩니다.

---

## 🔄 4단계: 배포 및 업데이트

코드가 수정되었을 때 다음 명령어로 서버를 업데이트할 수 있습니다.

```bash
chmod +x scripts/deploy_ec2.sh
./scripts/deploy_ec2.sh
```

---

## 🔍 상태 확인 및 문제 해결

*   **서비스 상태 확인**:
    ```bash
    sudo supervisorctl status
    ```
    `storyproof-backend`, `storyproof-celery`가 `RUNNING` 상태여야 합니다.

*   **로그 확인**:
    *   백엔드 로그: `tail -f /var/log/storyproof/backend.err.log`
    *   Celery 로그: `tail -f /var/log/storyproof/celery.err.log`
    *   Nginx 로그: `tail -f /var/log/nginx/error.log`

*   **Nginx 재시작**:
    ```bash
    sudo systemctl restart nginx
    ```

## 🌐 접속 확인

브라우저에서 `http://YOUR_SERVER_IP` 로 접속하여 StoryProof가 정상 동작하는지 확인합니다.
