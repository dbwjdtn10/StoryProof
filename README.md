# StoryProof


## 실행순서
1. 벡엔드 실행 : uvicorn main:app --reload
2. 프론트엔드 실행 : npm run dev
3. 설정오류탐지 기능 실행 전 : terminal 에서 wsl -> sudo service redis-server start -> redis-cli ping 후 pong 이 나오면 실행완료
4. 설정오류탐지 기능 서버 실행 : StoryProof-main/start_server
5. 설정오류탐지 기능 실행 : StoryProof-main/start_worker

=> 총 5개 terminal 열림


## 비동기 작동순서


## 스토리 예측 모델 : 질문과 관련된 부분만 찾아내서 읽는 방식(rag)

< 프론트 엔드 >
"StoryProof-main\frontend\src\components\PredictionSidebar.tsx"
FloatingMenu.tsx => 화면 하단에 나오는 버튼 
chapterDetail.tsx  => 설정파괴 탐지기 

<벡엔드>
StoryProof-main\backend\api\v1\endpoints\chat.py


## 설정파괴 탐지기
