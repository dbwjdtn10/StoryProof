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


<벡엔드>

StoryProof-main\backend\api\v1\endpoints\chat.py

StoryProof-main\backend\services\chatbot_service.py ==> 함수정의

StoryProof-main\backend\schemas\chat_schema.py ==> 요청과 응답 


## 스토리 예측 모델 동작원리
1. 전처리 (사전 작업): 소설 전체 내용을 '씬(Scene)'이나 일정 단위로 쪼개서 임베딩(숫자 데이터)으로 변환한 뒤 Pinecone에 저장해 둡니다.

2. 검색 (Retrieval): 사용자가 "다음 내용은 어떻게 될까?"라고 물으면, 백엔드는 그 질문과 가장 유사하거나 맥락이 이어지는 일부 장면들만 Pinecone에서 찾아냅니다.

3. 답변 생성 (Generation): 찾아낸 특정 장면들(Context)과 사용자의 질문을 Gemini AI에게 전달하여 "이 내용을 바탕으로 예측해줘"라고 요청합니다.




## 설정파괴 탐지기

< 프론트 엔드 >

chapterDetail.tsx  => 설정파괴 탐지기 

< 벡엔드 >

backend/worker/celery_app.py => 비동기 처리 작업실행

backend\worker\tasks.py => Celery 비동기 작업 정의

backend/services/agent.py  => agent 정의 및 실행

backend/services/chatbot_service.py => 챗봇 실행

backend/services/analysis/ => 분석 엔진 
