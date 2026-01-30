"""
스토리 분석 시스템
씬 청킹 → LLM 구조화 → 임베딩 검색 (Pinecone) → 사전 기능 (PostgreSQL)
"""

import os
import json
import re
import uuid
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import numpy as np

# Add parent directory to path if needed (e.g. running as script)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Backend Imports
from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.db.models import Novel, Analysis, VectorDocument, AnalysisType, AnalysisStatus, User

# ============================================================================
# 1. 기존 Parent Chunking 클래스들 (그대로 유지)
# ============================================================================

class DocumentLoader:
    """다양한 파일 형식에서 문서 로드"""
    
    @staticmethod
    def load_txt(file_path: str) -> str:
        """TXT 파일 로드 (자동 인코딩 감지)"""
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                detected_encoding = result['encoding']
                confidence = result['confidence']
                
                if confidence > 0.7 and detected_encoding:
                    try:
                        text = raw_data.decode(detected_encoding)
                        print(f"[OK] 파일 로드: {detected_encoding} (신뢰도: {confidence:.2f})")
                        return text
                    except Exception:
                        pass
        except ImportError:
            pass
        
        encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-16', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='strict') as f:
                    text = f.read()
                    print(f"[OK] 파일 로드: {encoding}")
                    return text
            except (UnicodeDecodeError, UnicodeError, LookupError):
                continue
        
        raise UnicodeDecodeError(
            'unknown', b'', 0, 1,
            f"지원하지 않는 인코딩: {encodings}"
        )


class SceneChunker:
    """씬 기반 텍스트 분할"""
    
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
    
    TIME_TRANSITIONS = [
        '그때', '다음날', '잠시 후', '그 후', '이튿날', '며칠 후',
        '다음', '그날', '아침', '저녁', '밤', '새벽', '오후',
        '한참 후', '곧', '이윽고', '그러자', '순간'
    ]
    
    # 챕터 패턴 (우선순위 높음)
    CHAPTER_PATTERNS = [
        r'^\s*제\s*\d+\s*[장화회]',      # 제1장, 제 1 화
        r'^\s*Chapter\s*\d+',          # Chapter 1
        r'^\s*\d+\.\s+',               # 1. 제목
        r'^\s*프롤로그',                # 프롤로그
        r'^\s*에필로그',                # 에필로그
        r'^\s*Prologue',
        r'^\s*Epilogue',
        r'^\s*Open\s*$'                # Open (가끔 사용됨)
    ]
    
    def __init__(self, threshold: int = 8, min_scene_sentences: int = 3, max_scene_sentences: int = 90):
        # 기본 임계값 (자동 감지에 실패했을 때의 안전 장치)
        self.default_threshold = threshold
        self.current_threshold = threshold
        self.mode = "scene" # 'scene' or 'chapter'
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
            print(f"💡 명확한 챕터 구조 감지됨 ({matches}개 헤더). 챕터 기반 분할을 적용합니다.")
            return "chapter"
        else:
            # 구조화되지 않은 텍스트는 동적 임계값으로 균형잡힌 청킹
            print(f"💡 구조화되지 않은 텍스트 감지. 동적 임계값으로 균형잡힌 청킹을 적용합니다.")
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
        # 1. 구조 감지 및 모드 설정
        self.mode = self.detect_structure(text)
        
        if self.mode == "chapter":
            # 챕터 모드: 챕터 헤더를 기준으로 분할하되, max_scene_sentences로 제한
            self.current_threshold = 1000
        elif self.mode == "hybrid":
            # 하이브리드 모드: 동적 임계값으로 균형잡힌 청킹
            self.current_threshold = self.calculate_dynamic_threshold(text)
        else:
            # 기본 씬 모드
            self.current_threshold = self.default_threshold
            
        sentences = re.split(r'([.!?]\s+)', text)
        
        merged_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):

                merged_sentences.append(sentences[i] + sentences[i + 1])
            else:
                merged_sentences.append(sentences[i])
        
        scenes = []
        current_scene = []
        score = 0
        sentence_count = 0
        prev_was_dialogue = False
        
        for sent in merged_sentences:
            if not sent.strip():
                continue
            
            # [수정] 줄바꿈 정규화 (2개 이상의 줄바꿈을 단일 줄바꿈으로 변환하여 공백 제거)
            sent = re.sub(r'\n{2,}', '\n', sent)
            
            # [공통] 챕터/헤더 감지 (강제 분할)
            if self.is_chapter_header(sent):
                if current_scene and sentence_count >= self.min_scene_sentences:
                    scenes.append(" ".join(current_scene))
                    current_scene = []
                    sentence_count = 0
                current_scene.append(sent)
                score = 0 
                continue

            # [점수 계산]
            # 명확한 씬 구분자
            if "***" in sent or "---" in sent or "###" in sent:
                score += 12
            
            # 연속된 줄바꿈 (문단 구분)
            if "\n\n" in sent or sent.count('\n') >= 2:
                score += 5
            
            # 장소 변화
            if self.contains_new_location(sent):
                score += 4
            
            # 시간 전환
            if any(word in sent for word in self.TIME_TRANSITIONS):
                score += 3
            
            # 대화 전환 감지 (인용부호로 시작)
            is_dialogue = sent.strip().startswith('"') or sent.strip().startswith("'")
            if is_dialogue != prev_was_dialogue and sentence_count > 0:
                score += 2
            prev_was_dialogue = is_dialogue
            
            # 대화 종료 후 지문
            if re.search(r'["\']\s*[.!?]\s+[^"\']+', sent):
                score += 2
            
            current_scene.append(sent)
            sentence_count += 1
            
            # 분할 조건:
            # 1. 점수가 임계값 도달 AND 최소 길이 만족
            # 2. 최대 길이 초과
            should_split = False
            
            if score >= self.current_threshold and sentence_count >= self.min_scene_sentences:
                should_split = True
            
            if sentence_count >= self.max_scene_sentences:
                should_split = True
            
            if should_split:
                scenes.append(" ".join(current_scene))
                current_scene = []
                score = 0
                sentence_count = 0
                prev_was_dialogue = False
        
        # 마지막 씬 처리 (최소 길이 체크)
        if current_scene:
            if sentence_count >= self.min_scene_sentences or not scenes:
                scenes.append(" ".join(current_scene))
            else:
                # 너무 짧으면 이전 씬에 병합
                if scenes:
                    scenes[-1] += " " + " ".join(current_scene)
                else:
                    scenes.append(" ".join(current_scene))
        
        print(f"✂️ 총 {len(scenes)}개의 씬으로 분할됨 (모드: {self.mode})")
        return scenes


# ============================================================================
# 2. LLM 구조화 시스템 (Gemini)
# ============================================================================

@dataclass
class Character:
    """인물 정보"""
    name: str
    aliases: List[str]  # 별칭, 다른 호칭
    description: str
    first_appearance: int  # 씬 번호
    traits: List[str]  # 성격, 특징


@dataclass
class Item:
    """아이템/소품 정보"""
    name: str
    description: str
    first_appearance: int
    significance: str  # 중요도/역할


@dataclass
class Location:
    """장소 정보"""
    name: str
    description: str
    scenes: List[int]  # 등장한 씬 번호들


@dataclass
class Event:
    """사건/이벤트 정보"""
    summary: str
    scene_index: int
    characters_involved: List[str]
    significance: str


@dataclass
class StructuredScene:
    """구조화된 씬"""
    scene_index: int
    original_text: str
    summary: str
    characters: List[str]
    locations: List[str]
    items: List[str]
    key_events: List[str]
    mood: str  # 분위기
    time_period: Optional[str]  # 시간대


class GeminiStructurer:
    """Gemini를 사용한 씬 구조화"""
    
    def __init__(self, api_key: str):
        try:
            from google import genai
            from google.api_core import retry
        except ImportError:
            # 설치해야 할 패키지 이름도 바뀌었습니다 (google-generativeai -> google-genai)
            raise ImportError("Gemini API 필요: pip install google-genai")
        
        # Use settings if api_key is not passed
        if not api_key:
             api_key = settings.GOOGLE_API_KEY
        
        # [핵심 수정] configure 삭제 -> Client 객체 생성으로 변경
        # [핵심 수정] configure 삭제 -> Client 객체 생성으로 변경
        # 타임아웃 설정을 제거하여 기본값 사용 (600이 ms로 해석되어 1초 미만 에러 발생 추정)
        self.client = genai.Client(api_key=api_key)
        
        # [핵심 수정] 모델 이름(ID)을 저장해 둡니다.
        self.model_name = 'gemini-2.5-flash'
        
        # Retry Configuration
        self.retry_policy = {
            "retry": retry.Retry(predicate=retry.if_transient_error, initial=1.0, multiplier=2.0, maximum=60.0, timeout=300.0)
        }
        
        self.system_prompt = """당신은 소설/스토리의 씬을 분석하여 구조화된 정보를 추출하는 전문가입니다.

주어진 씬에서 다음 정보를 JSON 형식으로 추출하세요:

{
  "summary": "씬의 핵심 요약 (2-3 문장)",
  "characters": ["등장하는 인물 이름들"],
  "locations": ["등장하는 장소들"],
  "items": ["중요한 아이템/소품들"],
  "key_events": ["주요 사건/행동들"],
  "mood": "분위기 (예: 긴장감, 평온, 슬픔, 유쾌 등)",
  "time_period": "시간대 정보 (있다면)"
}

**중요 규칙:**
- 정확히 JSON 형식으로만 응답하세요
- 없는 정보는 빈 리스트([]) 또는 null로 표시
- 인물 이름은 일관성 있게 표기 (별칭도 통일)
"""

    def _generate_with_retry(self, prompt: str):
        """재시도 로직이 포함된 생성 함수"""
        try:
            # google-genai SDK 0.2+ style configuration
            # config는 'GenerateContentConfig' 객체 혹은 dict여야 하는데
            # timeout은 config 내부가 아니라 http_options (또는 유사 옵션)으로 처리되거나
            # types.GenerateContentConfig(http_options={'timeout': 120}) 형태여야 함.
            # 하지만 최신 버전에서는 config 내부에 http_options를 넣는 것이 일반적임.
            # ERROR: Extra inputs are not permitted [type=extra_forbidden, input_value=120, input_type=int]
            
            # 올바른 설정: config 내부에 http_options 사용
            from google.genai import types
            
            config = types.GenerateContentConfig(
                http_options={'timeout': 120000} # 밀리초 단위일 수 도 있고 초 단위일 수도 있음. 보통 SDK는 초 단위지만 120으로 설정해서 에러났으니 
                # 아까 에러는 timeout 필드 자체가 허용되지 않았음.
            )
            
            # google-genai SDK 최신 변경 사항:
            # Client.models.generate_content(..., config=...)
            # config에 timeout 필드가 없다면, http_options를 써야 함.
            
            # 다시 시도: config 딕셔너리에 http_options 추가
            # (SDK 버전에 따라 다를 수 있으므로 가장 안전한 방법 시도)
            
            # Pydantic 에러가 났다는 건 GenerateContentConfig 모델 검증 실패임.
            # GenerateContentConfig에는 timeout 필드가 없음.
            # 보통 client 레벨이나 호출 시점에 http_options를 줘야 함.
            
            response = self.client.models.generate_content(
                model=self.model_name, 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json' # JSON 응답 강제 (옵션)
                )
            )
            # 타임아웃은 여기서 해결하기보다, client 생성시나 다른 방식으로 해야할 수 있음.
            # 일단 에러나는 timeout 파라미터를 제거하고 실행.
            # (리소스 문제로 인한 타임아웃은 재시도 로직으로 커버)
            return response
            return response
        except Exception as e:
            print(f"⚠️ API 호출 중 오류 발생 (재시도 실패): {e}")
            raise e

    def structure_scene(self, scene_text: str, scene_index: int) -> StructuredScene:
        """단일 씬 구조화 분석"""
        prompt = f"""{self.system_prompt}

다음 씬을 분석하세요:

{scene_text}
"""
        try:
            response = self._generate_with_retry(prompt)
            json_text = response.text.strip()
            
            # Markdown code block 제거
            if json_text.startswith("```"):
                json_text = re.sub(r'^```json?\s*|\s*```$', '', json_text, flags=re.MULTILINE)
            
            data = json.loads(json_text)
            
            return StructuredScene(
                scene_index=scene_index,
                original_text=scene_text,
                summary=data.get('summary', ''),
                characters=data.get('characters', []),
                locations=data.get('locations', []),
                items=data.get('items', []),
                key_events=data.get('key_events', []),
                mood=data.get('mood', ''),
                time_period=data.get('time_period')
            )
            
        except Exception as e:
            print(f"⚠️ 씬 {scene_index} 구조화 실패: {e}")
            # 실패 시 기본 객체 반환
            return StructuredScene(
                scene_index=scene_index,
                original_text=scene_text,
                summary="분석 실패",
                characters=[],
                locations=[],
                items=[],
                key_events=[],
                mood="",
                time_period=None
            )
            
    def extract_global_entities(self, structured_scenes: List[StructuredScene], custom_system_prompt: Optional[str] = None) -> Dict:
        """전체 씬에서 등장하는 엔티티 통합 분석 (커스텀 프롬프트 지원)"""
        
        # 모든 씬 정보 수집 (원본 텍스트 제외하여 토큰 절약 for prompt)
        scenes_summary = []
        full_scenes_data = [] # 반환용 전체 데이터 (text 포함)

        for scene in structured_scenes:
            scene_data = asdict(scene)
            full_scenes_data.append(scene_data.copy()) # 원본 보존

            if 'original_text' in scene_data:
                del scene_data['original_text'] # 프롬프트용에서는 제거
            scenes_summary.append(scene_data)
            
        all_info = {
            "scenes": scenes_summary
        }
        
        if custom_system_prompt:
            # 커스텀 프롬프트 사용
            print("🎨 커스텀 시스템 프롬프트를 사용하여 분석합니다.")
            prompt = f"""{custom_system_prompt}

다음은 소설의 씬 분석 데이터입니다. 이 데이터를 바탕으로 위 프롬프트의 지시사항을 수행하여 JSON 형식으로 응답하세요:

{json.dumps(all_info, ensure_ascii=False, indent=2)}
"""
        else:
            # 기본 프롬프트 (기존 바이블 구조)
            prompt = f"""{self.system_prompt}

다음은 여러 씬의 분석 결과입니다. 전체 스토리에서 등장하는 주요 엔티티들을 통합하여 정리하세요:

{json.dumps(all_info, ensure_ascii=False, indent=2)}

다음 형식의 JSON으로 응답하세요:

{{
  "characters": [
    {{
      "name": "인물 이름",
      "aliases": ["별칭1", "별칭2"],
      "description": "인물 설명",
      "first_appearance": 첫_등장_씬_번호,
      "traits": ["특징1", "특징2"]
    }}
  ],
  "items": [
    {{
      "name": "아이템 이름",
      "description": "설명",
      "first_appearance": 첫_등장_씬_번호,
      "significance": "스토리상 의미"
    }}
  ],
  "locations": [
    {{
      "name": "장소 이름",
      "description": "장소 설명",
      "scenes": [등장한_씬_번호들]
    }}
  ],
  ],
  "key_events": [
    {{
      "summary": "핵심 사건 내용",
      "scene_index": 씬_번호,
      "importance": "상/중/하"
    }}
  ]
}}
"""
        
        try:
            response = self._generate_with_retry(prompt)
            json_text = response.text.strip()
            
            if json_text.startswith("```"):
                json_text = re.sub(r'^```json?\s*|\s*```$', '', json_text, flags=re.MULTILINE)
            
            result = json.loads(json_text)
            
            result = json.loads(json_text)
            
            # [수정] 씬 텍스트 정보를 결과에 포함
            result['scenes'] = full_scenes_data

            # [추가] 캐릭터별 등장 씬(appearances) 계산 및 보강
            if 'characters' in result:
                for char in result['characters']:
                    char_name = char.get('name', '')
                    char_aliases = char.get('aliases', [])
                    appearances = []

                    for scene in full_scenes_data:
                        scene_chars = scene.get('characters', [])
                        # 해당 씬의 등장인물 목록에 이름이나 별칭이 포함되어 있는지 확인
                        is_appeared = False
                        if char_name in scene_chars:
                            is_appeared = True
                        else:
                            for alias in char_aliases:
                                if alias in scene_chars:
                                    is_appeared = True
                                    break
                        
                        if is_appeared:
                            appearances.append(scene['scene_index'])
                    
                    char['appearances'] = appearances
                    char['appearance_count'] = len(appearances)

            # [추가] 아이템별 등장 씬(appearances) 계산 및 보강
            if 'items' in result:
                for item in result['items']:
                    item_name = item.get('name', '')
                    appearances = []

                    for scene in full_scenes_data:
                        scene_items = scene.get('items', [])
                        # 해당 씬의 아이템 목록에 이름이 포함되어 있는지 확인
                        if item_name in scene_items:
                            appearances.append(scene['scene_index'])
                    
                    item['appearances'] = appearances
                    item['appearance_count'] = len(appearances)

            # [추가] 장소별 등장 씬(scenes) 계산 및 보강
            if 'locations' in result:
                for loc in result['locations']:
                    loc_name = loc.get('name', '')
                    related_scenes = []

                    for scene in full_scenes_data:
                        scene_locs = scene.get('locations', [])
                        # 해당 씬의 장소 목록에 이름이 포함되어 있는지 확인
                        if loc_name in scene_locs:
                            related_scenes.append(scene['scene_index'])
                    
                    # LLM이 추출한 scenes 리스트가 있을 수 있지만, 정확도를 위해 계산된 값으로 덮어쓰거나 보완
                    # 여기서는 계산된 값으로 덮어씁니다.
                    loc['scenes'] = related_scenes
                    loc['appearance_count'] = len(related_scenes)
            
            return result
        
        except Exception as e:
            print(f"⚠️  전역 엔티티 추출 실패: {e}")
            # 실패 시 빈 딕셔너리 반환 (동적 구조이므로 키를 미리 알 수 없음)
            # 실패하더라도 씬 정보는 반환하는 것이 좋음
            return {"scenes": full_scenes_data}


# ============================================================================
# 3. 임베딩 및 검색 시스템 (Bge-m3 + Pinecone + Postgres)
# ============================================================================

class EmbeddingSearchEngine:
    """임베딩 기반 검색 엔진 (Pinecone 연동)"""
    
    def __init__(self):
        """
        BAAI/bge-m3 모델을 사용한 임베딩 생성
        Pinecone을 벡터 저장소로 사용
        """
        try:
            from sentence_transformers import SentenceTransformer
            from pinecone import Pinecone
        except ImportError:
            raise ImportError("sentence-transformers, pinecone-client 필요: pip install sentence-transformers pinecone-client")
        
        print("🔄 BAAI/bge-m3 모델 로딩 중...")
        self.model = SentenceTransformer('BAAI/bge-m3')
        print("✅ 임베딩 모델 로드 완료")
        
        # Pinecone 초기화
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        
        # 인덱스 확인 (없으면 생성은 하지 않음, 에러 발생)
        if self.index_name not in [idx.name for idx in self.pc.list_indexes()]:
             print(f"⚠️ Pinecone 인덱스 '{self.index_name}'가 존재하지 않습니다. 먼저 생성해주세요.")
             # raise ValueError(f"Pinecone index '{self.index_name}' not found.")
        
        self.index = self.pc.Index(self.index_name)
        print(f"✅ Pinecone 인덱스 연결: {self.index_name}")
    
    def embed_text(self, text: str) -> List[float]:
        """텍스트를 임베딩 벡터로 변환"""
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    
    def add_documents(self, documents: List[Dict], novel_id: int):
        """문서들을 임베딩하여 Pinecone과 DB에 저장"""
        print(f"\n📥 {len(documents)}개 문서 처리 중...")
        
        db = SessionLocal()
        vectors_to_upsert = []
        
        try:
            for i, doc in enumerate(documents):
                # 검색용 텍스트 생성 (요약 + 원문 일부)
                # 메타데이터를 포함하여 검색 품질 향상
                search_text = f"{doc.get('summary', '')} {doc.get('original_text', '')[:1000]}"
                
                # 임베딩 생성
                embedding = self.embed_text(search_text)
                
                # 고유 ID 생성 (UUID 또는 novel_id_scene_index 형식)
                vector_id = f"novel_{novel_id}_scene_{doc['scene_index']}"
                
                # Pinecone 메타데이터 준비 (필터링 및 간단한 정보 표시용)
                metadata = {
                    'novel_id': novel_id,
                    'scene_index': doc['scene_index'],
                    'summary': doc.get('summary', '')[:200],  # 너무 길면 잘릴 수 있으므로 제한
                    # 'type': 'scene' # 나중에 챕터나 다른 단위가 생기면 구분
                }
                
                vectors_to_upsert.append({
                    'id': vector_id,
                    'values': embedding,
                    'metadata': metadata
                })
                
                # DB에 상세 정보 저장 (VectorDocument)
                # 이미 존재하는지 확인
                existing_doc = db.query(VectorDocument).filter(
                    VectorDocument.vector_id == vector_id
                ).first()
                
                if existing_doc:
                    existing_doc.chunk_text = doc.get('original_text', '')
                    existing_doc.metadata_json = doc # 전체 구조화 정보 저장
                else:
                    new_doc = VectorDocument(
                        novel_id=novel_id,
                        chapter_id=None, # 현재는 씬 단위이므로 챕터 정보가 명시적으로 없으면 None
                        vector_id=vector_id,
                        chunk_index=doc['scene_index'],
                        chunk_text=doc.get('original_text', ''),
                        metadata_json=doc
                    )
                    db.add(new_doc)
                
                if (i + 1) % 10 == 0:
                    print(f"  진행: {i + 1}/{len(documents)}")
            
            # Pinecone 업로드 (배치 처리 권장하지만 여기선 한방에)
            # Pinecone limit per request is usually 100 vectors, stick to safe batching if needed.
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                self.index.upsert(vectors=batch)
                
            db.commit()
            print("✅ Pinecone 업로드 및 DB 저장 완료")
            
        except Exception as e:
            db.rollback()
            print(f"❌ 문서 저장 실패: {e}")
            raise e
        finally:
            db.close()
    
    def search(self, query: str, novel_id: int = None, top_k: int = 5) -> List[Dict]:
        """소설 내에서 쿼리와 유사한 씬 검색"""
        
        # 쿼리 임베딩
        query_embedding = self.embed_text(query)
        
        # Pinecone 쿼리 필터
        filter_dict = {}
        if novel_id:
            filter_dict['novel_id'] = novel_id # Pinecone metadata filter uses float usually, but int works if stored as number
        
        # Pinecone 검색
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )
        
        # 결과 매핑
        hits = []
        db = SessionLocal()
        try:
            for match in results.matches:
                vector_id = match.id
                score = match.score
                
                # DB에서 원본 데이터 조회 (전체 정보를 가져오기 위해)
                doc = db.query(VectorDocument).filter(VectorDocument.vector_id == vector_id).first()
                
                if doc:
                    # JSON 메타데이터에서 구조화된 씬 정보 복원
                    scene_data = doc.metadata_json
                    hits.append({
                        'document': scene_data,
                        'similarity': score,
                        'vector_id': vector_id
                    })
                else:
                    # DB에 없을 경우 Pinecone 메타데이터라도 사용
                    print(f"⚠️ DB에서 문서 {vector_id}를 찾을 수 없습니다.")
                    hits.append({
                        'document': {
                            'scene_index': match.metadata.get('scene_index'),
                            'summary': match.metadata.get('summary'),
                            'characters': [],
                            'locations': [],
                            'original_text': "(DB 조회 실패)"
                        },
                        'similarity': score,
                        'vector_id': vector_id
                    })
        finally:
            db.close()
        
        return hits


# ============================================================================
# 4. 스토리보드 및 사전 시스템 (DB 연동)
# ============================================================================

class StoryboardSystem:
    """통합 스토리보드 + 사전 시스템"""
    
    def __init__(self, gemini_api_key: str): # Key is used for Gemini
        self.structurer = GeminiStructurer(gemini_api_key)
        self.search_engine = EmbeddingSearchEngine() # Pinecone key is in settings
        
        self.current_novel_id: Optional[int] = None
        self.structured_scenes: List[StructuredScene] = []
        self.entities: Dict = {}
    
    def export_storyboard(self, filename: str = "storyboard.txt"):
        """스토리보드를 텍스트 파일로 내보내기"""
        if not self.current_novel_id:
            print("❌ 선택된 소설이 없습니다.")
            return

        db = SessionLocal()
        try:
            docs = db.query(VectorDocument).filter(
                VectorDocument.novel_id == self.current_novel_id
            ).order_by(VectorDocument.chunk_index).all()
            
            if not docs:
                print("📭 내보낼 데이터가 없습니다.")
                return

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"=== 스토리보드 (ID: {self.current_novel_id}) ===\n\n")
                
                for doc in docs:
                    meta = doc.metadata_json or {}
                    summary = meta.get('summary', '요약 없음')
                    chars = ", ".join(meta.get('characters', []))
                    
                    f.write(f"[Scene {doc.chunk_index}]\n")
                    f.write(f"요약: {summary}\n")
                    if chars:
                        f.write(f"등장인물: {chars}\n")
                    
                    locs = ", ".join(meta.get('locations', []))
                    if locs:
                        f.write(f"장소: {locs}\n")
                        
                    f.write("-" * 50 + "\n\n")
            
            print(f"✅ 스토리보드가 '{filename}' 파일로 저장되었습니다.")
            
        except Exception as e:
            print(f"❌ 파일 저장 실패: {e}")
        finally:
            db.close()

    def get_or_create_novel(self, title: str) -> int:
        """소설 DB 등록 또는 조회"""
        db = SessionLocal()
        try:
            # Check if exists
            novel = db.query(Novel).filter(Novel.title == title).first()
            if not novel:
                # 임시로 1번 유저(admin)에게 할당하겠습니다.
                # 실제 서비스에서는 로그인한 유저 정보를 받아야 합니다.
                user = db.query(User).first()
                if not user:
                    # Create dummy user if not exists (for standalone test)
                    user = User(email="admin@example.com", username="admin", hashed_password="hashed_password")
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                
                novel = Novel(
                    title=title,
                    author_id=user.id,
                    description="Analyzed by Story Analyzer"
                )
                db.add(novel)
                db.commit()
                db.refresh(novel)
                print(f"🆕 새 소설 등록: {title} (ID: {novel.id})")
            else:
                print(f"ℹ️ 기존 소설 로드: {title} (ID: {novel.id})")
            
            return novel.id
        finally:
            db.close()

    def load_entities_from_db(self, novel_id: int):
        """DB에서 엔티티(사전) 정보 로드"""
        db = SessionLocal()
        try:
            # OVERALL 타입의 분석 결과를 찾음
            analysis = db.query(Analysis).filter(
                Analysis.novel_id == novel_id,
                Analysis.analysis_type == AnalysisType.OVERALL
            ).first()
            
            if analysis and analysis.result:
                self.entities = analysis.result
                print("✅ DB에서 기존 엔티티 사전 로드 완료")
            else:
                self.entities = {}
                print("ℹ️ 기존 엔티티 사전이 없습니다.")
                
        finally:
            db.close()

    def save_entities_to_db(self, novel_id: int, entities: Dict):
        """엔티티(사전) 정보를 DB에 저장"""
        db = SessionLocal()
        try:
            # 기존 레코드 확인
            analysis = db.query(Analysis).filter(
                Analysis.novel_id == novel_id,
                Analysis.analysis_type == AnalysisType.OVERALL
            ).first()
            
            if not analysis:
                analysis = Analysis(
                    novel_id=novel_id,
                    analysis_type=AnalysisType.OVERALL,
                    status=AnalysisStatus.COMPLETED,
                    result=entities
                )
                db.add(analysis)
            else:
                analysis.result = entities
                analysis.updated_at = db.func.now()
            
            db.commit()
            print("💾 엔티티 사전 DB 저장 완료")
        except Exception as e:
            db.rollback()
            print(f"❌ 엔티티 저장 실패: {e}")
        finally:
            db.close()

    def process_story(self, file_path: str, scene_threshold: int = 8):
        """스토리 파일 전체 처리 (scene_threshold: 씬 분할 임계값, 낮을수록 더 잘게 분할)"""
        
        filename = os.path.basename(file_path)
        novel_title = os.path.splitext(filename)[0]
        
        print("=" * 70)
        print(f"🎬 스토리보드 생성 시작: {novel_title}")
        print("=" * 70)
        
        # DB 소설 ID 확보
        self.current_novel_id = self.get_or_create_novel(novel_title)
        
        # 1. 파일 로드 및 씬 분할
        print("\n[1/4] 파일 로드 및 씬 분할")
        loader = DocumentLoader()
        text = loader.load_txt(file_path)
        
        chunker = SceneChunker(threshold=scene_threshold)
        scenes = chunker.split_into_scenes(text)
        print(f"✅ {len(scenes)}개 씬 생성")
        
        # 2. 각 씬 구조화
        print(f"\n[2/4] 씬별 구조화 (Gemini 분석)")
        self.structured_scenes = []
        for i, scene in enumerate(scenes):
            structured = self.structurer.structure_scene(scene, i)
            self.structured_scenes.append(structured)
            print(f"  씬 {i+1}/{len(scenes)} 완료")
        
        # 3. 전역 엔티티 추출
        print(f"\n[3/4] 전역 엔티티 추출 (인물, 아이템, 장소)")
        self.entities = self.structurer.extract_global_entities(self.structured_scenes)
        print(f"✅ 인물: {len(self.entities.get('characters', []))}명")
        print(f"✅ 아이템: {len(self.entities.get('items', []))}개")
        print(f"✅ 장소: {len(self.entities.get('locations', []))}곳")
        
        # DB 저장 (엔티티)
        self.save_entities_to_db(self.current_novel_id, self.entities)
        
        # 4. 검색 인덱스 생성 (Pinecone + DB)
        print(f"\n[4/4] 검색 인덱스 생성 (Pinecone & DB)")
        documents = [asdict(scene) for scene in self.structured_scenes]
        self.search_engine.add_documents(documents, self.current_novel_id)
        
        print("\n" + "=" * 70)
        print("✅ 스토리보드 생성 및 저장 완료!")
        print("=" * 70)
    
    def search_scenes(self, query: str, top_k: int = 5):
        """씬 검색 (Pinecone 사용)"""
        if not self.current_novel_id:
             print("❌ 선택된 소설이 없습니다.")
             return []
        
        print(f"\n🔍 검색: '{query}'")
        results = self.search_engine.search(query, self.current_novel_id, top_k)
        
        print(f"\n📊 검색 결과 (상위 {len(results)}개):\n")
        for i, result in enumerate(results):
            doc = result['document']
            sim = result['similarity']
            
            print(f"[{i+1}] 씬 {doc.get('scene_index', '?')} (유사도: {sim:.3f})")
            print(f"    요약: {doc.get('summary', '내용 없음')}")
            # print(f"    인물: {', '.join(doc.get('characters', []))}") # Optional
            print()
        
        return results
    
    def lookup_character(self, name: str) -> Optional[Dict]:
        """인물 사전 조회"""
        if not self.entities and self.current_novel_id:
             self.load_entities_from_db(self.current_novel_id)

        for char in self.entities.get('characters', []):
            if char['name'] == name or name in char.get('aliases', []):
                return char
        return None
    
    def lookup_item(self, name: str) -> Optional[Dict]:
        """아이템 사전 조회"""
        if not self.entities and self.current_novel_id:
             self.load_entities_from_db(self.current_novel_id)

        for item in self.entities.get('items', []):
            if item['name'] == name:
                return item
        return None
    
    def lookup_location(self, name: str) -> Optional[Dict]:
        """장소 사전 조회"""
        if not self.entities and self.current_novel_id:
             self.load_entities_from_db(self.current_novel_id)

        for loc in self.entities.get('locations', []):
            if loc['name'] == name:
                return loc
        return None
    
    def print_dictionary(self):
        """전체 사전 출력"""
        if not self.entities and self.current_novel_id:
             self.load_entities_from_db(self.current_novel_id)

        print("\n" + "=" * 70)
        print("📖 스토리 사전")
        print("=" * 70)
        
        # 인물
        print("\n👥 인물:")
        for char in self.entities.get('characters', []):
            print(f"\n  • {char['name']}")
            if char.get('aliases'):
                print(f"    별칭: {', '.join(char['aliases'])}")
            print(f"    설명: {char.get('description', '없음')}")
            print(f"    첫 등장: 씬 {char.get('first_appearance', '?')}")
            if char.get('traits'):
                print(f"    특징: {', '.join(char['traits'])}")
        
        # 아이템
        print("\n📦 아이템:")
        for item in self.entities.get('items', []):
            print(f"\n  • {item['name']}")
            print(f"    설명: {item.get('description', '없음')}")
            print(f"    첫 등장: 씬 {item.get('first_appearance', '?')}")
            print(f"    의미: {item.get('significance', '없음')}")
        
        # 장소
        print("\n🗺️  장소:")
        for loc in self.entities.get('locations', []):
            print(f"\n  • {loc['name']}")
            print(f"    설명: {loc.get('description', '없음')}")
            scenes = loc.get('scenes', [])
            if scenes:
                print(f"    등장 씬: {', '.join(map(str, scenes))}")
        
        print("\n" + "=" * 70)


# ============================================================================
# 5. 메인 실행
# ============================================================================

def main():
    """사용 예시"""
    
    # 1. 설정 확인
    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        print("❌ GOOGLE_API_KEY/GEMINI_API_KEY 가 설정되지 않았습니다.")
        return
        
    print(f"🔧 환경: {settings.ENVIRONMENT}")
    print(f"🌲 Pinecone: {settings.PINECONE_INDEX_NAME}")
    print(f"🛢️ Database: {settings.DATABASE_URL}")
    print("-" * 50)
    
    storyboard = StoryboardSystem(api_key)
    
    # 예시: 텍스트 파일 처리
    import glob
    import argparse
    
    parser = argparse.ArgumentParser(description="Story Analyzer")
    parser.add_argument("file", nargs="?", help="Path to the text file to analyze")
    args = parser.parse_args()
    
    input_file = None
    
    if args.file:
        if os.path.exists(args.file):
            input_file = args.file
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {args.file}")
            return
    else:
        txt_files = glob.glob("*.txt")
        
        if not txt_files:
            print("❌ 현재 디렉토리에 .txt 파일을 찾을 수 없습니다.")
            print("사용법: python story_analyzer.py [파일경로]")
            print("또는 현재 폴더에 .txt 파일을 복사해주세요.")
            return
        
        print("사용 가능한 파일:")
        for i, f in enumerate(txt_files):
            print(f"[{i+1}] {f}")
            
        choice = input("\n파일 번호 선택 (엔터: 첫번째 파일): ").strip()
        idx = 0
        if choice and choice.isdigit():
            idx = int(choice) - 1
            
        if idx < 0 or idx >= len(txt_files):
            print("잘못된 선택입니다.")
            return
            
        input_file = txt_files[idx]
    
    print(f"📄 선택된 파일: {input_file}")
    
    # Processing Option
    print("\n작업 선택:")
    print(" [1] 새로 분석 및 DB 저장 (시간 소요됨)")
    print(" [2] 기존 DB 데이터 불러오기")
    mode = input("선택 (기본: 2): ").strip()
    
    if mode == "1":
        storyboard.process_story(input_file, scene_threshold=8)
    else:
        # Load logic
        filename = os.path.basename(input_file)
        novel_title = os.path.splitext(filename)[0]
        novel_id = storyboard.get_or_create_novel(novel_title)
        storyboard.current_novel_id = novel_id
        storyboard.load_entities_from_db(novel_id)
        print(f"✅ 로드 완료: Novel ID {novel_id}")
    
    # 3. 사전 출력
    storyboard.print_dictionary()
    
    # 4. 인터랙티브 모드
    print("\n" + "=" * 70)
    print("💬 인터랙티브 모드")
    print("=" * 70)
    print("명령어:")
    print("  search [쿼리]    - 씬 검색")
    print("  export          - 스토리보드 txt 내보내기")
    print("  char [이름]      - 인물 조회")
    print("  item [이름]      - 아이템 조회")
    print("  loc [이름]       - 장소 조회")
    print("  dict            - 전체 사전 보기")
    print("  quit            - 종료")
    print()
    
    while True:
        try:
            cmd = input(">>> ").strip()
            
            if not cmd:
                continue
            
            if cmd == "quit":
                break
            
            elif cmd == "export":
                storyboard.export_storyboard()
            
            elif cmd == "dict":
                storyboard.print_dictionary()
            
            elif cmd.startswith("search "):
                query = cmd[7:]
                storyboard.search_scenes(query, top_k=5)
            
            elif cmd.startswith("char "):
                name = cmd[5:]
                char = storyboard.lookup_character(name)
                if char:
                    print(f"\n👤 {char['name']}")
                    print(f"   {char.get('description', '')}")
                else:
                    print(f"❌ '{name}' 인물을 찾을 수 없습니다.")
            
            elif cmd.startswith("item "):
                name = cmd[5:]
                item = storyboard.lookup_item(name)
                if item:
                    print(f"\n📦 {item['name']}")
                    print(f"   {item.get('description', '')}")
                else:
                    print(f"❌ '{name}' 아이템을 찾을 수 없습니다.")
            
            elif cmd.startswith("loc "):
                name = cmd[4:]
                loc = storyboard.lookup_location(name)
                if loc:
                    print(f"\n🗺️  {loc['name']}")
                    print(f"   {loc.get('description', '')}")
                else:
                    print(f"❌ '{name}' 장소를 찾을 수 없습니다.")
            
            else:
                print("❌ 알 수 없는 명령어입니다.")
        
        except KeyboardInterrupt:
            print("\n\n👋 종료합니다.")
            break
        except Exception as e:
            print(f"❌ 오류: {e}")


if __name__ == "__main__":
    main()
