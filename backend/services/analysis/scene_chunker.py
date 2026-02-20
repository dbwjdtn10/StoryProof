"""
씬 청킹 모듈
===========
소설 텍스트를 의미 있는 씬(장면) 단위로 분할합니다.

주요 기능:
1. 자동 구조 감지 (챕터 기반 vs 씬 기반)
2. 동적 임계값 계산 (텍스트 특성에 따라 자동 조정)
3. 다양한 씬 구분 휴리스틱 (장소, 시간, 대화 전환 등)

청킹 전략:
- 챕터 모드: 명확한 챕터 헤더가 있는 경우
- 하이브리드 모드: 구조화되지 않은 텍스트 (동적 임계값 사용)
- 씬 모드: 기본 모드 (고정 임계값)

목표: 청크당 약 3,000자 유지 (너무 작거나 크지 않게)
"""

import re
from typing import List


class SceneChunker:
    """
    씬 기반 텍스트 분할 클래스
    
    소설 텍스트를 의미 있는 씬(장면) 단위로 분할합니다.
    단순히 글자 수나 문장 수로 나누는 것이 아니라,
    장소 변화, 시간 전환, 대화 패턴 등을 분석하여 자연스러운 경계를 찾습니다.
    
    분할 기준:
    - 챕터 헤더 (제1장, Chapter 1 등)
    - 장소 키워드 (방, 거리, 숲 등 100+ 키워드)
    - 시간 전환 (다음날, 그때, 잠시 후 등)
    - 대화 전환 (지문 → 대화, 대화 → 지문)
    - 씬 구분자 (***, ---, ### 등)
    
    Attributes:
        LOCATION_KEYWORDS (List[str]): 장소 변화를 감지하는 키워드 목록
        TIME_TRANSITIONS (List[str]): 시간 전환을 나타내는 표현 목록
        CHAPTER_PATTERNS (List[str]): 챕터 헤더를 감지하는 정규식 패턴
        default_threshold (int): 기본 점수 임계값
        current_threshold (int): 현재 사용 중인 점수 임계값
        mode (str): 분할 모드 ('scene', 'chapter', 'hybrid')
        min_scene_sentences (int): 씬의 최소 문장 수
        max_scene_sentences (int): 씬의 최대 문장 수
    """
    
    # 장소 키워드: 100개 이상의 다양한 공간 표현
    # 실내, 건물, 상업시설, 교통, 자연, 판타지 등 장르별 키워드 포함
    LOCATION_KEYWORDS = [
        # 🏠 실내 / 주거
        '방', '집', '거실', '침실', '부엌', '주방', '욕실', '화장실',
        '현관', '다락', '지하실', '베란다', '마당', '옥상',

        # 🏢 건물 / 시설
        '건물', '사무실', '회사', '회의실', '강당', '연구실',
        '병원', '응급실', '수술실', '약국',
        '학교', '교실', '교정', '도서관',
        '경찰서', '법원', '감옥', '구치소',
        '은행', '우체국',

        # 🍽 상업 / 공공 공간
        '카페', '식당', '술집', '바', '포장마차',
        '상점', '가게', '시장', '마트', '백화점',
        '호텔', '모텔', '여관', '숙소', '로비',

        # 🚉 교통 / 이동
        '거리', '골목', '도로', '교차로',
        '역', '지하철역', '정류장',
        '공항', '터미널', '항구', '부두',
        '차 안', '열차 안', '버스 안',

        # 🌆 지역 / 행정 단위
        '마을', '동네', '도시', '시내', '외곽',
        '지역', '구역', '지구',

        # 🌲 자연 / 야외
        '공원', '광장',
        '숲', '산', '언덕', '계곡',
        '강', '호수', '바다', '해변',
        '들판', '초원', '사막', '동굴',

        # 🏰 서사 / 장르 특화 (판타지·사극·무협)
        '성', '성벽', '성문', '궁', '궁전', '왕궁',
        '탑', '신전', '사원', '제단',
        '마법진', '던전', '유적',
        '무덤', '묘지', '폐허',
        '객잔', '주막', '서원',
        '전장', '진영', '야영지',

        # 🌌 추상적·경계 공간 (의미 전환용)
        '안', '밖', '내부', '외부',
        '근처', '맞은편', '저편', '건너편'
    ]
    
    # 시간 전환 표현: 씬 경계를 나타내는 시간 관련 표현
    TIME_TRANSITIONS = [
        '그때', '다음날', '잠시 후', '그 후', '이튿날', '며칠 후',
        '다음', '그날', '아침', '저녁', '밤', '새벽', '오후',
        '한참 후', '곧', '이윽고', '그러자', '순간'
    ]
    
    # 챕터 패턴: 명확한 챕터 구분을 감지하는 정규식
    CHAPTER_PATTERNS = [
        r'^\s*제\s*\d+\s*[장화회]',      # 제1장, 제 1 화
        r'^\s*\d+\s*장\.?',            # 1장, 1장. (모비딕 등 지원)
        r'^\s*Chapter\s*\d+',          # Chapter 1
        r'^\s*CHAPTER\s*\d+',          # CHAPTER 1
        r'^\s*\d+\.\s+',               # 1. 제목
        r'^\s*프롤로그',                # 프롤로그
        r'^\s*에필로그',                # 에필로그
        r'^\s*Prologue',
        r'^\s*Epilogue',
        r'^\s*Open\s*$'                # Open (가끔 사용됨)
    ]
    
    def __init__(self, threshold: int = 8, min_scene_sentences: int = 3, max_scene_sentences: int = 90):
        """
        씬 청커 초기화
        
        Args:
            threshold (int): 기본 점수 임계값 (기본값: 8)
                           점수가 이 값을 넘으면 씬 분할
            min_scene_sentences (int): 씬의 최소 문장 수 (기본값: 3)
                                      너무 짧은 씬 방지
            max_scene_sentences (int): 씬의 최대 문장 수 (기본값: 90)
                                      너무 긴 씬 강제 분할
        """
        # 기본 임계값 (자동 감지에 실패했을 때의 안전 장치)
        self.default_threshold = threshold
        self.current_threshold = threshold
        self.mode = "scene"  # 'scene', 'chapter', 'hybrid' 중 하나
        self.min_scene_sentences = min_scene_sentences  # 최소 씬 길이
        self.max_scene_sentences = max_scene_sentences  # 최대 씬 길이 (청크당 약 3,000글자 목표)
        self.target_chunk_size = 3000  # 목표 청크 크기 (글자 수)
    
    def contains_new_location(self, sentence: str) -> bool:
        return any(loc in sentence for loc in self.LOCATION_KEYWORDS)

    def is_chapter_header(self, sentence: str) -> bool:
        """문장이 챕터 헤더인지 확인"""
        sentence = sentence.strip()
        if len(sentence) > 60:
            return False
            
        for pattern in self.CHAPTER_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                return True
        return False
        
    def detect_structure(self, text: str) -> str:
        """텍스트 구조를 분석하여 적절한 모드 결정"""
        # 전체 텍스트에서 챕터 헤더 패턴이 몇 번이나 나오는지 샘플링
        
        matches = 0
        lines = text.split('\n')
        sample_lines = lines[:3000]
        
        for line in sample_lines:
            if self.is_chapter_header(line):
                matches += 1
        
        # 명확한 챕터 구조 감지 (2개 이상 찾았을 때만)
        if matches >= 2:
            print(f"[INFO] 명확한 챕터 구조 감지됨 ({matches}개 헤더). 챕터 기반 분할을 적용합니다.")
            return "chapter"
        else:
            # 구조화되지 않은 텍스트는 동적 임계값으로 균형잡힌 청킹
            print(f"[INFO] 구조화되지 않은 텍스트 감지. 동적 임계값으로 균형잡힌 청킹을 적용합니다.")
            return "hybrid"  # 새로운 하이브리드 모드
    
    def calculate_dynamic_threshold(self, text: str) -> int:
        """
        텍스트의 특성에 따라 동적 임계값 계산
        목표: 소설 크기와 관계없이 균형잡힌 청킹 유지 (청크당 약 700-800글자)
        
        실험 결과:
        - 임계값 15: 청크당 ~550글자 (앨리스/지킬 모두 기준)
        - 임계값 20: 청크당 ~730-740글자 ✓ (권장)
        - 임계값 25: 청크당 ~900-920글자 (큰 소설용)
        
        문장 길이와 텍스트 구조에 따라 중간값을 찾아 적용
        """
        import statistics
        
        # 문장 단위 분할
        sentences = re.split(r'([.!?]\s+)', text)
        merged_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                merged_sentences.append(sentences[i] + sentences[i + 1])
            else:
                merged_sentences.append(sentences[i])
        
        merged_sentences = [s.strip() for s in merged_sentences if s.strip()]
        
        # 각 문장의 길이 측정
        sentence_lengths = [len(s) for s in merged_sentences]
        
        if not sentence_lengths:
            return 18  # 기본값 (균형잡힌 중간값)
        
        # 통계 계산
        avg_sentence_length = statistics.mean(sentence_lengths)
        median_sentence_length = statistics.median(sentence_lengths)
        
        if median_sentence_length == 0:
            return 18
        
        # 중간값 기준으로 임계값 동적 조정 (3,000글자 목표)
        # 문장이 짧을수록 → 임계값 높게 (더 많은 문장을 모음)
        # 문장이 길수록 → 임계값 낮게 (더 적게 모음)
        
        # 목표: 청크당 3,000글자
        # 필요한 문장 개수 계산
        target_chunk_size = 3000
        needed_sentences = max(40, target_chunk_size / (median_sentence_length or 1))
        
        # 임계값은 문장 개수에 따라 설정
        # 높은 배수를 적용해서 덜 분할되도록 함 (더 큰 청크)
        calculated_threshold = max(225, int(needed_sentences * 2.4))
        
        # 범위 제한 (225~340)
        calculated_threshold = min(calculated_threshold, 340)
        
        print(f"  📊 동적 임계값 계산 (3,000글자 목표):")
        print(f"     - 평균 문장 길이: {avg_sentence_length:.0f}글자")
        print(f"     - 중앙값 문장 길이: {median_sentence_length:.0f}글자")
        print(f"     - 필요 문장 개수: {needed_sentences:.0f}개")
        print(f"     - 적용 임계값: {calculated_threshold}")
        
        return calculated_threshold
    
    def split_into_scenes(self, text: str) -> List[str]:
        """
        간소화된 씬 분할: LLM 챕터 헤더 감지만 사용
        
        - 챕터 헤더가 있으면: 챕터별로 분할
        - 챕터 헤더가 없으면: 전체를 하나의 Parent Scene으로 사용
        """
        # 1. 챕터 구조 감지
        self.mode = self.detect_structure(text)
        
        # 2. 챕터 헤더가 없으면 전체를 하나의 씬으로 반환
        if self.mode != "chapter":
            print(f"[INFO] 챕터 구조 없음. 전체를 1개 Parent Scene으로 사용합니다.")
            return [text]
        
        # 3. 챕터 헤더 기반 분할
        print(f"[INFO] 챕터 구조 감지됨. 챕터별로 분할합니다.")
        
        # 문장 단위로 분할
        sentences = re.split(r'([.!?]\s+)', text)
        
        merged_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                merged_sentences.append(sentences[i] + sentences[i + 1])
            else:
                merged_sentences.append(sentences[i])
        
        # 챕터 헤더로만 분할
        scenes = []
        current_scene = []
        
        for sent in merged_sentences:
            if not sent.strip():
                continue
            
            # 챕터 헤더 감지 시 새로운 씬 시작
            if self.is_chapter_header(sent):
                if current_scene:
                    scenes.append(" ".join(current_scene))
                    current_scene = []
                current_scene.append(sent)
            else:
                current_scene.append(sent)
        
        # 마지막 씬 추가
        if current_scene:
            scenes.append(" ".join(current_scene))
        
        # 결과가 없으면 전체를 하나의 씬으로
        if not scenes:
            scenes = [text]
        
        print(f"[OK] 총 {len(scenes)}개의 Parent Scene으로 분할됨 (모드: {self.mode})")
        return scenes
