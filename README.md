# StoryProof


## 실행순서
1. 벡엔드 실행 : uvicorn main:app --reload
2. 프론트엔드 실행 : npm run dev
3. 설정오류탐지 기능 실행 전 : command 에서 wsl -> sudo service redis-server start -> redis-cli ping 후 pong 이 나오면 실행완료
4. 설정오류탐지 기능 서버 실행 : StoryProof-main/start_server
5. 설정오류탐지 기능 실행 : StoryProof-main/start_worker
