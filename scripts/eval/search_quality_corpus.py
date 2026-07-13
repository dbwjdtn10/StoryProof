"""
검색 품질 평가셋 — 멀티챕터 테스트 소설 + 질문-정답 쌍

`scripts/eval_search_quality.py`가 이 코퍼스를 색인하고 각 질문을 실제
Q&A 파이프라인(chatbot_service.ask)에 던져 채점한다.

설계 의도:
- 4개 챕터로 BM25 코퍼스 크기를 SEARCH_MIN_BM25_CORPUS_SIZE(5) 근처로 만들어
  하이브리드 검색(BM25+dense) 경로와 dense-only 폴백 경로를 모두 관찰 가능하게 함
- "스포일러 방지" 케이스: 뒤 챕터에만 나오는 사실을 앞 챕터로 스코프 제한해 질문
  → 못 찾아야 정상(회차 필터가 실제로 걸리는지 검증)
- "본문에 없는 사실" 케이스: 이야기에 전혀 없는 내용을 질문 → "찾을 수 없음"
  응답이 나와야 정상(허구 생성/환각 방지 게이트 검증)
"""

CHAPTERS = [
    {
        "chapter_number": 1,
        "title": "1화. 달빛 조각술",
        "content": """
달빛이 공방의 창을 넘어 들어왔다. 위드는 조각칼을 내려놓고 이마의 땀을 닦았다.
그의 손에는 방금 완성한 달의 여신상이 들려 있었다. 은은한 빛이 조각상에서 흘러나왔다.

"드디어... 걸작이 나왔군."

위드는 왕국 제일의 조각사가 되기 위해 로자임 왕국의 수도를 떠나 3년째 방랑 중이었다.
그의 스승 자흐렌은 떠나는 그에게 낡은 조각칼 하나를 건네며 말했었다.
"조각은 손이 아니라 마음으로 하는 것이다. 네가 그것을 깨닫는 날, 이 칼이 대답할 것이다."

그날 밤, 여관에서 위드는 이상한 꿈을 꾸었다. 달의 여신 헤스티아가 나타나 속삭였다.
"나의 모습을 새긴 자여, 그대에게 달빛 조각술을 허락하노라."

깨어난 위드의 손에는 스승의 조각칼이 푸른 달빛으로 빛나고 있었다.
공방 밖에서는 왕국 기사단장 페일이 그를 찾아와 문을 두드리고 있었다.
"위드 님, 국왕 폐하께서 왕궁 대전에 세울 조각상을 의뢰하고자 하십니다."

위드는 조각칼을 쥐었다. 새로운 이야기가 시작되고 있었다.
""".strip(),
    },
    {
        "chapter_number": 2,
        "title": "2화. 수도의 라이벌",
        "content": """
로자임 왕국의 수도 세라핌은 위드가 기억하던 것보다 훨씬 화려했다. 페일과 함께
왕궁으로 향하던 위드는 광장에서 낯선 여인과 부딪혔다. 검을 등에 멘 그녀는
위드를 위아래로 훑어보더니 코웃음을 쳤다.

"당신이 소문의 그 조각사? 왕실 조각사 자리를 노린다면 나, 서윤을 넘어야 할 거예요."

서윤은 왕국 제일의 여기사이자 스스로도 조각에 일가견이 있다고 자부하는 인물이었다.
그녀는 위드에게 사흘 뒤 열릴 조각 경연에서 실력을 겨루자고 제안했다.

왕궁에 도착한 위드와 페일을 맞이한 것은 국왕의 시종장 헤인이었다. 헤인은 깐깐한
성격으로 유명했지만, 위드의 조각칼을 보고는 눈을 빛냈다.
"자흐렌 님의 제자시군요. 폐하께서 기다리고 계십니다."
""".strip(),
    },
    {
        "chapter_number": 3,
        "title": "3화. 재상의 음모",
        "content": """
경연 전날 밤, 위드는 작업실에서 홀로 조각상의 밑그림을 다듬고 있었다. 그때
문틈으로 그림자 하나가 스며들었다. 국왕의 재상 바트로였다.

바트로는 왕실의 재정을 담당하며 오랫동안 뒷돈을 챙겨온 인물로, 새로운 왕실
조각사가 자신의 비리를 파헤칠까 두려워하고 있었다. 그는 위드의 조각칼을
훔치려다 실패하자, 대신 작업실에 불을 지르라고 부하에게 명령했다.

"조각사만 없으면 이 계획도 없던 일이 될 것이다."

다행히 순찰을 돌던 페일이 수상한 낌새를 눈치채고 불을 미리 꺼뜨렸다. 위드는
자신을 노린 것이 우연이 아님을 직감했다. 헤인도 은밀히 위드에게 귀띔했다.
"재상을 조심하십시오. 그는 이전에도 방해가 되는 자들을 여럿 쫓아냈습니다."
""".strip(),
    },
    {
        "chapter_number": 4,
        "title": "4화. 왕실 조각사",
        "content": """
경연 당일, 위드는 서윤과 나란히 조각상을 선보였다. 위드의 달빛 조각술이
만들어낸 작품은 은은한 빛을 내뿜으며 대전을 가득 채웠다. 서윤조차 감탄을
감추지 못하고 박수를 보냈다.

그 순간, 바트로가 보낸 자객들이 경연장에 난입했다. 페일과 서윤이 힘을 합쳐
자객들을 제압했고, 위드는 조각칼로 마지막 자객의 검을 막아냈다. 헤인이
증거를 들이밀자 바트로의 비리가 만천하에 드러났고, 그는 왕궁에서 추방되었다.

국왕은 위드에게 "왕실 조각사"의 칭호를 내렸다. 서윤은 위드에게 다가와 말했다.
"다음엔 진짜로 겨뤄봐요. 그땐 안 봐줄 거예요." 위드는 웃으며 고개를 끄덕였다.
""".strip(),
    },
]


# expect: "found" (정상적으로 답을 찾아야 함) | "not_found" (못 찾아야 정상)
# chapter_scope: None(전체 검색) | 1~4(해당 챕터로 회차 필터)
# expected_keywords: found 케이스에서 답변에 하나 이상 포함되어야 하는 키워드
QA_PAIRS = [
    {
        "id": "ch1-master",
        "question": "위드의 스승은 누구야?",
        "chapter_scope": None,
        "expect": "found",
        "expected_keywords": ["자흐렌"],
    },
    {
        "id": "ch1-goddess",
        "question": "위드가 꿈에서 만난 존재는?",
        "chapter_scope": None,
        "expect": "found",
        "expected_keywords": ["헤스티아", "여신"],
    },
    {
        "id": "ch2-rival",
        "question": "위드가 수도에서 처음 만난 라이벌은 누구야?",
        "chapter_scope": None,
        "expect": "found",
        "expected_keywords": ["서윤"],
    },
    {
        "id": "ch2-chamberlain",
        "question": "국왕의 시종장 이름은?",
        "chapter_scope": None,
        "expect": "found",
        "expected_keywords": ["헤인"],
    },
    {
        "id": "ch3-villain",
        "question": "위드의 작업실에 불을 지르라고 명령한 사람은 누구야?",
        "chapter_scope": None,
        "expect": "found",
        "expected_keywords": ["바트로"],
    },
    {
        "id": "ch3-villain-role",
        "question": "바트로의 직책은 뭐야?",
        "chapter_scope": None,
        "expect": "found",
        "expected_keywords": ["재상"],
    },
    {
        "id": "ch4-title",
        "question": "위드가 국왕에게 받은 칭호는?",
        "chapter_scope": None,
        "expect": "found",
        "expected_keywords": ["왕실 조각사"],
    },
    {
        "id": "ch4-scoped-found",
        "question": "위드가 국왕에게 받은 칭호는?",
        "chapter_scope": 4,
        "expect": "found",
        "expected_keywords": ["왕실 조각사"],
    },
    {
        "id": "spoiler-ch4-fact-scoped-ch1",
        "question": "위드가 국왕에게 받은 칭호는?",
        "chapter_scope": 1,
        "expect": "not_found",
        "expected_keywords": [],
    },
    {
        "id": "spoiler-ch3-villain-scoped-ch2",
        "question": "위드의 작업실에 불을 지르라고 명령한 사람은 누구야?",
        "chapter_scope": 2,
        "expect": "not_found",
        "expected_keywords": [],
    },
    {
        "id": "no-answer-father",
        "question": "위드의 아버지 이름은 뭐야?",
        "chapter_scope": None,
        "expect": "not_found",
        "expected_keywords": [],
    },
    {
        "id": "no-answer-unrelated",
        "question": "위드가 좋아하는 음식은 뭐야?",
        "chapter_scope": None,
        "expect": "not_found",
        "expected_keywords": [],
    },
]
