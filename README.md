2\. 팀원 초기 설정 (Getting Started)

팀원이 프로젝트를 처음 받아서 실행할 때의 단계입니다.



환경 변수 설정



cp .env.example .env

\# .env 파일을 열어 자신의 설정(DB 비밀번호, API 키 등)을 입력합니다.

Docker DB 실행



docker-compose up -d

-d: 백그라운드 실행

DB가 5432 포트로 실행됩니다.

DB 접속 확인



DBeaver나 VS Code Database 확장 프로그램 등을 사용해 localhost:5432에 접속해봅니다.

설정 정보는 

.env

에 입력한 내용과 일치해야 합니다.

3\. Docker 명령어 모음

자주 사용하는 Docker Compose 명령어입니다.



실행 (백그라운드): docker-compose up -d

실행 (로그 보기): docker-compose up (종료하려면 Ctrl+C)

중지 및 삭제: docker-compose down (컨테이너 삭제, 데이터는 volume에 남음)

재빌드 후 실행: docker-compose up -d --build (이미지 변경 시)

로그 확인: docker-compose logs -f \[서비스명] (예: docker-compose logs -f db)

상태 확인: docker-compose ps

4\. Alembic \& .env 설정 방법

Alembic은 DB 스키마 변경을 코드로 관리하는 도구입니다. 각 팀원의 로컬 DB 설정이 다르더라도 

.env

를 통해 안전하게 연결할 수 있습니다.



4.1 Alembic 초기화 (아직 안 했다면)

cd backend

alembic init alembic

4.2 env.py 설정 (중요!)

backend/alembic/env.py 파일을 수정하여 

.env

&nbsp;값을 읽어오도록 설정해야 합니다. 기본 설정은 하드코딩된 주소를 사용하므로, 아래와 같이 변경합니다.



\# backend/alembic/env.py 상단에 추가

import os

import sys

from logging.config import fileConfig

from sqlalchemy import engine\_from\_config

from sqlalchemy import pool

from alembic import context

\# 1. 프로젝트 경로 추가 (app 모듈 import를 위해)

sys.path.append(os.getcwd())

\# 2. config 로드 (app/core/config.py 또는 .env 직접 로드)

\# 방법 A: config.py의 settings 사용 (추천)

from app.core.config import settings

config = context.config

\# 3. sqlalchemy.url 덮어쓰기

config.set\_main\_option("sqlalchemy.url", settings.DATABASE\_URL)

\# ... 나머지 기존 코드 ...

\# target\_metadata 설정 (autogenerate를 위해 필수)

from app.db.models import Base  # models.py 위치에 맞게 수정

target\_metadata = Base.metadata

\# ...

4.3 마이그레이션 명령어

스키마 변경사항 생성 (models.py 수정 후):



alembic revision --autogenerate -m "Add user table"

생성된 파일은 backend/alembic/versions/에 저장되며, Git에 커밋해야 합니다.



내 DB에 적용 (최신 상태로):



alembic upgrade head

적용 취소 (한 단계 뒤로):



alembic downgrade -1

