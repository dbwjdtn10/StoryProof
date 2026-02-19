# gcloud CLI 인식 문제 해결 가이드

## 문제 상황
PowerShell에서 `gcloud` 명령어가 인식되지 않음

## 해결 방법

### 방법 1: PowerShell 재시작 ⭐ (가장 간단)

1. 현재 PowerShell 창을 **완전히 종료**
2. 새로운 PowerShell 창 열기
3. 다음 명령어로 확인:
   ```powershell
   gcloud version
   ```

> 💡 gcloud CLI 설치 후 PATH가 업데이트되었지만, 현재 세션에는 반영되지 않았을 수 있습니다.

---

### 방법 2: gcloud CLI 재설치

설치가 완료되지 않았을 수 있습니다.

1. **설치 프로그램 다운로드**
   - [Google Cloud SDK 설치 페이지](https://cloud.google.com/sdk/docs/install)
   - Windows용 설치 프로그램 다운로드

2. **설치 시 주의사항**
   - ✅ "Add gcloud to PATH" 옵션 체크
   - ✅ "Run gcloud init" 옵션 체크 (선택)

3. **설치 완료 후**
   - PowerShell 재시작
   - `gcloud version` 명령어로 확인

---

### 방법 3: 수동으로 PATH 추가

gcloud가 설치되어 있지만 PATH에 없는 경우:

#### 3-1. gcloud 설치 위치 찾기

일반적인 설치 위치:
- `C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin`
- `C:\Users\[사용자명]\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin`

PowerShell에서 검색:
```powershell
Get-ChildItem -Path "C:\" -Recurse -Filter "gcloud.cmd" -ErrorAction SilentlyContinue | Select-Object FullName
```

#### 3-2. PATH에 수동 추가

**임시 추가 (현재 세션만):**
```powershell
$env:PATH += ";C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin"
gcloud version
```

**영구 추가 (시스템 전체):**
```powershell
# 관리자 권한으로 PowerShell 실행 후
[Environment]::SetEnvironmentVariable(
    "Path",
    $env:Path + ";C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin",
    [EnvironmentVariableTarget]::Machine
)
```

> ⚠️ 위 경로는 예시입니다. 실제 gcloud가 설치된 경로로 변경하세요.

---

### 방법 4: 전체 경로로 직접 실행

PATH 설정 없이 바로 실행:

```powershell
# gcloud.cmd 파일을 직접 실행
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" projects list
```

---

## 설치 확인

다음 명령어들이 모두 작동하면 성공:

```powershell
# 버전 확인
gcloud version

# 로그인 상태 확인
gcloud auth list

# 프로젝트 목록
gcloud projects list
```

---

## 여전히 안 되는 경우

1. **컴퓨터 재시작**
   - 환경 변수 변경이 완전히 반영되지 않았을 수 있습니다.

2. **Windows Terminal 사용**
   - 기본 PowerShell 대신 Windows Terminal 사용 시도

3. **관리자 권한으로 실행**
   - PowerShell을 관리자 권한으로 실행

---

## 다음 단계

gcloud가 정상 작동하면:

```powershell
# 1. 로그인
gcloud auth login

# 2. 프로젝트 확인
gcloud projects list

# 3. 배포 진행
.\setup-secrets.ps1 -ProjectId YOUR-PROJECT-ID
.\deploy.ps1 -ProjectId YOUR-PROJECT-ID
```
