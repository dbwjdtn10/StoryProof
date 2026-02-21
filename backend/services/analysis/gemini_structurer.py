"""
Gemini LLM 구조화 모듈
Google Gemini API를 사용하여 씬을 분석하고 구조화된 정보를 추출합니다.
"""

import json
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

from backend.core.config import settings


# ============================================================================
# 데이터 클래스 정의
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
    characters: List[Dict] # [{"name": "...", "description": "...", "traits": ["..."]}]
    relationships: List[Dict]  # [{"source": "...", "target": "...", "relation": "...", "description": "..."}]
    locations: List[Dict]
    items: List[Dict]
    key_events: List[Dict]
    mood: str  # 분위기
    time_period: Optional[str]  # 시간대


# ============================================================================
# Gemini 구조화 클래스
# ============================================================================

class GeminiStructurer:
    """Gemini를 사용한 씬 구조화"""
    
    def __init__(self, api_key: str = None):
        try:
            from google import genai
            from google.api_core import retry
        except ImportError:
            raise ImportError("Gemini API 필요: pip install google-genai")
        
        # Use settings if api_key is not passed
        if not api_key:
            api_key = settings.GOOGLE_API_KEY
        
        self.client = genai.Client(api_key=api_key)
        self.model_name = settings.GEMINI_STRUCTURING_MODEL
        
        # Retry Configuration
        self.retry_policy = {
            "retry": retry.Retry(
                predicate=retry.if_transient_error,
                initial=1.0,
                multiplier=2.0,
                maximum=60.0,
                timeout=300.0
            )
        }
        
        self.system_prompt = """당신은 소설/스토리의 씬을 분석하여 구조화된 정보를 추출하는 전문가입니다.

주어진 씬에서 다음 정보를 JSON 형식으로 추출하세요:

{
  "summary": "씬의 핵심 요약 (2-3문장. 누가 무엇을 왜 했는지, 결과는 어떠한지 포함)",
  "characters": [{"name": "인물 이름", "description": "이 씬에서의 행동과 감정 상태 (1-2문장)", "visual_description": "외모 묘사 (머리색, 눈색, 체형, 복장, 나이대, 인상 등 시각적 특징을 최대한 상세하게. 언급 없으면 빈 문자열)", "traits": ["특성1", "특성2"]}],
  "relationships": [{"source": "인물A", "target": "인물B", "relation": "관계 유형 (예: 연인, 적대, 상하, 동료, 가족)", "description": "이 씬에서 드러나는 두 인물의 관계 묘사"}],
  "locations": [{"name": "장소 이름", "description": "장소 묘사", "visual_description": "장소의 시각적 묘사 (건축 양식, 분위기, 조명, 색감, 크기 등)"}],
  "items": [{"name": "아이템 이름", "description": "용도/의미", "visual_description": "아이템의 시각적 묘사 (재질, 색상, 크기, 형태, 장식 등)"}],
  "key_events": [{"summary": "사건 내용 (원인→경과→결과 구조로)", "importance": "상/중/하"}],
  "mood": "분위기 (예: 긴장감, 평온, 슬픔, 유쾌 등)",
  "time_period": "시간대 정보 (있다면)"
}

**중요 규칙:**
- 정확히 JSON 형식으로만 응답
- 없는 정보는 빈 리스트([]) 또는 null로 표시
- 인물 이름은 일관성 있게 표기:
  * 경칭/호칭 제거: "씨", "님", "선생님", "교수", "박사", "군", "양" 등을 제거한 순수 이름만 사용 (예: "어터슨 씨" → "어터슨", "김 박사" → "김")
  * 영문 경칭도 제거: "Mr.", "Ms.", "Dr." 등 (예: "Mr. Hyde" → "Hyde")
  * 같은 인물의 별칭/다른 표기를 대표 이름 하나로 통일 (예: "Utterson", "어터슨 씨" → "어터슨")
- visual_description은 이미지 생성에 사용되므로, 소설 본문에서 언급된 외모/시각적 정보를 최대한 구체적으로 추출
- relationships는 이 씬에서 상호작용하는 인물 쌍만 추출 (단순 언급은 제외)
- summary에는 핵심 갈등이나 변화를 반드시 포함
"""

    def _generate_with_retry(self, prompt: str):
        """재시도 로직이 포함된 생성 함수"""
        try:
            from google.genai import types
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,  # 일관성을 위해 0으로 설정 (결정론적 출력 유도)
                    response_mime_type='application/json'  # JSON 응답 강제
                )
            )
            return response
        except Exception as e:
            print(f"[Error] API 호출 중 오류 발생 (재시도 실패): {e}")
            raise e

    def _detect_hard_anchors(self, text: str) -> List[str]:
        """
        정규표현식을 사용하여 명확한 장/절 구분(Hard Anchors)을 탐색합니다.
        목차(TOC)를 건너뛰고 본문의 챕터 헤더만 찾습니다.
        """
        # 1. 챕터 패턴 정의 (모든 변형 포함)
        patterns = [
            # 한글 숫자 패턴
            r'^제\s*\d+\s*장',                # 제1장, 제 1 장
            r'^\d+\s*장\.',                   # 1장. (숫자만)
            # 영어 숫자 패턴
            r'^Chapter\s+\d+',                # Chapter 1
            r'^CHAPTER\s+\d+',                # CHAPTER 54 (대문자)
            # 로마 숫자 패턴 (단독 라인) - 개츠비
            r'^[IVX]{1,8}\s*$',               # I, II, III, IV, V, VI, VII, VIII, IX, X 등
            r'^[IVXLCDM]{1,10}\s*$',          # 확장 로마 숫자 (최대 80까지)
            # 유니코드 로마 숫자 (개츠비)
            r'^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\s*$',           # Ⅰ, Ⅱ, Ⅲ, Ⅳ, Ⅴ, Ⅵ, Ⅶ, Ⅷ, Ⅸ, Ⅹ
            # 로마 숫자 + 마침표 + 제목 - 셜록
            r'^[IVX]{1,8}\.\s+',              # I. Title, II. Title
            r'^[IVXLCDM]{1,10}\.\s+',         # 확장 로마 숫자 + 제목
            # 한글 로마 숫자 (개츠비) - 단독
            r'^나\s*$',                        # I (한글)
            r'^다\s*$',                        # II (한글)
            r'^라\s*$',                        # III (한글)
            r'^뷔\s*$',                        # V (한글)
            # 단일 아라비아 숫자 (개츠비)
            r'^[1-9]\s*$',                     # 1, 2, 3, ..., 9
            # 에필로그
            r'^에필로그',
            r'^Epilogue',
            r'^EPILOGUE',
            # Markdown
            r'^#\s+',                         # Markdown H1
            r'^##\s+',                        # Markdown H2
        ]
        
        found_anchors = []
        lines = text.split('\n')
        
        # 2. 목차(TOC) 범위 찾기 - 목차 전체를 건너뛰기 위함
        toc_start_idx = -1
        toc_end_idx = 0
        consecutive_chapters = 0
        
        # 스캔 범위 확대 (500 -> 2000): 모비딕처럼 서문/목차가 긴 경우 대응
        scan_limit = 2000 
        
        for i, line in enumerate(lines[:scan_limit]):
            line_stripped = line.strip()
            if not line_stripped:
                # 빈 줄이라도 목차 중간일 수 있으므로 카운트 리셋하지 않음 (단, 너무 길면 리셋)
                continue
            
            # 목차 명시적 키워드 감지 (공백 포함 및 다양한 변형)
            if re.match(r'^\s*(목\s*차|차\s*례|Contents|Table\s+of\s+Contents)', line_stripped, re.IGNORECASE):
                toc_start_idx = i
                consecutive_chapters = 3  # 즉시 목차 모드로 진입
                continue

            # 챕터 패턴 매칭
            is_chapter = any(re.match(p, line_stripped, re.IGNORECASE) for p in patterns)
            
            if is_chapter:
                if consecutive_chapters == 0:
                    toc_start_idx = i
                consecutive_chapters += 1
                
                # 3개 이상 연속이면 목차로 간주 (개츠비는 4개)
                if consecutive_chapters >= 3:
                    # 목차 끝 찾기: 본문 시작 패턴 감지
                    last_chap_num = -1
                    # 현재 줄에서 번호 추출 시도
                    nm = re.search(r'\d+', line_stripped)
                    if nm:
                        last_chap_num = int(nm.group())

                    # 검색 범위를 현재 위치에서 +1000줄까지로 확대
                    for j in range(i + 1, min(i + 1000, len(lines))):
                        check_line = lines[j].strip()
                        if not check_line:
                            continue
                        
                        # 챕터 패턴이 아니면서 긴 문장이면 본문 시작
                        is_still_chapter = any(re.match(p, check_line, re.IGNORECASE) for p in patterns)
                        
                        if is_still_chapter:
                            # 번호 리셋 체크 (10장 -> 1장)
                            cur_nm = re.search(r'\d+', check_line)
                            if cur_nm and last_chap_num > 0:
                                cur_num = int(cur_nm.group())
                                # 번호가 갑자기 줄어들면 (예: 10 -> 1, 5 -> 1) 본문 시작으로 간주
                                if cur_num < last_chap_num:
                                     toc_end_idx = j
                                     print(f"   [TOC] 챕터 번호 리셋 감지 ({last_chap_num} -> {cur_num}). {toc_end_idx}번째 줄부터 본문으로 간주합니다.")
                                     break
                                last_chap_num = cur_num
                        
                        if not is_still_chapter and len(check_line) > 60:
                            toc_end_idx = j
                            print(f"   [TOC] 목차 감지됨 (Line {toc_start_idx}-{j}). {toc_end_idx}번째 줄부터 본문으로 간주합니다.")
                            break
                    break
            else:
                consecutive_chapters = 0
        
        # 3. 본문에서만 챕터 헤더 검색 (목차 범위는 완전히 건너뛰기)
        start_line = max(toc_end_idx, 0)
        
        for idx, line in enumerate(lines[start_line:], start=start_line):
            line_stripped = line.strip()
            if not line_stripped or len(line_stripped) > 100:  # 너무 긴 줄은 제목이 아님
                continue
            
            for p in patterns:
                if re.match(p, line_stripped, re.IGNORECASE):
                    # 최소 길이 체크
                    if len(line_stripped) >= 1:
                        # 이제 목차를 완전히 건너뛰었으므로 단순 중복만 체크
                        if line_stripped not in found_anchors:
                            found_anchors.append(line_stripped)
                    break
        
        if found_anchors:
            pass
        
        return found_anchors

    def split_scenes(self, text: str) -> List[str]:
        """
        LLM을 사용하여 텍스트를 씬 단위로 분할 (Anchor-based Approach)
        """
        # 0. 고정 앵커(Hard Anchors) 미리 탐색
        hard_anchors = self._detect_hard_anchors(text)
        hard_anchors_hint = ""
        if hard_anchors:
            hard_anchors_hint = f"\n**Confirmed Scene Starts (Use these as priority):**\n" + "\n".join([f"- {a}" for a in hard_anchors])

        # 텍스트 길이에 따른 동적 목표 갯수 계산
        # 보통 챕터 하나당 5,000자 ~ 8,000자 가정
        text_len = len(text)
        expected_min = max(3, text_len // 8000)
        expected_max = max(5, text_len // 4000)
        
        real_prompt = f"""Role: 당신은 전문 소설 편집자입니다.

Task: 아래 소설 전체를 읽고, **챕터/장(Chapter) 구분**의 시작 부분(첫 30-50자)을 찾아주세요.

**CRITICAL RULES (매우 중요):**
1. **CHAPTER HEADERS ONLY (챕터 헤더만):**
   - **오직 챕터/장 제목만** 찾으세요 (예: "제1장", "Chapter 1", "에필로그" 등)
   - 단순한 장면 전환, 장소 이동, 시간 경과는 **무시**하세요
   - 대화 전환, 인물 등장도 **무시**하세요
   
2. **USE DETECTED ANCHORS (감지된 앵커 우선 사용):**
{hard_anchors_hint}
   - 위 목록의 앵커들을 **반드시 포함**하세요
   - 이것들은 정규식으로 확인된 **확실한 챕터 헤더**입니다
   
3. **EXACT MATCH ONLY (정확히 일치해야 함):**
   - 반환하는 문자열은 원본 텍스트와 **100% 일치**해야 합니다
   - 단어 수정, 요약, 어미 변경 **절대 금지**
   - 원본을 그대로 복사하세요
   
4. **Anchor Length (길이):**
   - 챕터 제목의 **전체 또는 앞부분 30-50자**만 발췌하세요
   
5. **Expected Count (예상 개수):**
   - 정규식으로 {len(hard_anchors)}개의 챕터 헤더를 발견했습니다
   - 이 숫자와 **거의 일치**해야 합니다 (±5개 이내)
   - 만약 크게 다르다면, 챕터가 아닌 것을 포함했을 가능성이 높습니다

Original Text:
{text}

Output Format (JSON List of Strings):
["제1장. ...", "제2장. ...", "에필로그", ...]
"""
        try:
            print(f"--- LLM 씬 분할(Anchor 방식) 시작... (텍스트 길이: {len(text)}자)")
            
            # 긴 텍스트 처리를 위해 타임아웃/재시도 설정이 중요
            response = self._generate_with_retry(real_prompt)
            json_text = response.text.strip()
            
            if json_text.startswith("```"):
                json_text = re.sub(r'^```json?\s*|\s*```$', '', json_text, flags=re.MULTILINE)
            
            try:
                start_anchors = json.loads(json_text)
            except json.JSONDecodeError as e:
                print(f"!!! LLM 앵커 응답 JSON 파싱 실패: {e}")
                return [text]

            if not isinstance(start_anchors, list):
                print("!!! LLM 응답이 리스트가 아닙니다.")
                return [text]

            print(f"[Anchors] {len(start_anchors)}개의 씬 시작점(Anchor) 발견. 텍스트 슬라이싱 중...")
            
            scenes = []
            start_indices = []
            
            # 1. 각 앵커의 위치 찾기
            last_idx = -1
            text_len = len(text)
            
            for anchor in start_anchors:
                if not anchor or len(anchor.strip()) < 2:  # 최소 길이 2로 완화
                    continue
                    
                # A. 정확히 일치 (Exact Match)
                first_idx = text.find(anchor, last_idx + 1)

                if first_idx != -1:
                    idx = first_idx
                else:
                    idx = -1
                
                # B. 공백 정규화 및 부분 일치 (Whitespace Normalized Match)
                if idx == -1:
                    # 앵커의 앞 30자리만 추출하여 검색 (줄바꿈/공백 정규화)
                    clean_seed = re.sub(r'\s+', ' ', anchor).strip()[:30]
                    # 특수문자 이스케이프
                    pattern_str = re.escape(clean_seed).replace(r'\ ', r'\s+')
                    logging_pattern = re.compile(pattern_str)
                    
                    # 검색 범위 확대 (5000 -> 10000자)
                    search_limit = min(last_idx + 10000, len(text))
                    search_region = text[last_idx+1:search_limit]
                    
                    match = logging_pattern.search(search_region)
                    if match:
                        idx = last_idx + 1 + match.start()
                        print(f"    [Match] 부분/공백 정규화 매칭 성공: '{anchor[:15]}...'")

                # C. 장 번호 패턴 직접 매칭 (개선됨)
                if idx == -1:
                    # 앵커에서 장 번호 추출
                    chapter_patterns = [
                        r'제\s*(\d+)\s*장',      # 제1장, 제 1 장
                        r'^(\d+)\s*장',          # 1장, 5장
                        r'Chapter\s*(\d+)',      # Chapter 1
                        r'CHAPTER\s*(\d+)',      # CHAPTER 1
                        r'^([IVX]{1,8})\s*$',    # I, II, III (로마 숫자)
                        r'^([IVX]{1,8})\.',      # I., II.
                    ]
                    
                    chapter_num = None
                    for cp in chapter_patterns:
                        m = re.search(cp, anchor, re.IGNORECASE)
                        if m:
                            chapter_num = m.group(1)
                            break
                    
                    if chapter_num:
                        # 텍스트에서 같은 장 번호 찾기 (더 넓은 범위)
                        search_start = last_idx + 1
                        search_end = min(search_start + 15000, len(text))  # 범위 확대
                        search_region = text[search_start:search_end]
                        
                        # 여러 패턴으로 시도
                        search_patterns = [
                            rf'제\s*{chapter_num}\s*장',
                            rf'^{chapter_num}\s*장',
                            rf'Chapter\s*{chapter_num}',
                            rf'CHAPTER\s*{chapter_num}',
                        ]
                        
                        for sp in search_patterns:
                            chap_match = re.search(sp, search_region, re.MULTILINE | re.IGNORECASE)
                            if chap_match:
                                idx = search_start + chap_match.start()
                                print(f"    [Pattern Match] 장 번호 패턴 매칭 성공: '{chapter_num}장' at position {idx}")
                                break

                # D. 퍼지 매칭 (Fuzzy Match - difflib) - 개선됨
                if idx == -1:
                    import difflib
                    search_window = 5000  # 검색 범위 확대
                    search_start = last_idx + 1
                    search_end = min(search_start + search_window, len(text))
                    search_region = text[search_start:search_end]
                    
                    # 앵커가 '제N장' 이나 'Chapter' 로 시작하는지 확인
                    is_chapter = re.search(r'(제\s*\d+\s*장|Chapter\s*\d+|\d+\s*장)', anchor, re.IGNORECASE)
                    
                    if is_chapter:
                        # 장 번호 패턴으로 직접 검색 시도
                        chap_p = re.escape(is_chapter.group(0)).replace(r'\ ', r'\s+')
                        chap_match = re.search(chap_p, search_region, re.IGNORECASE)
                        if chap_match:
                            idx = search_start + chap_match.start()
                            print(f"    [Pattern Match] 장 번호 패턴 매칭 성공: '{anchor[:20]}...'")
                    
                    if idx == -1:
                        # difflib으로 유사한 부분 찾기
                        # 앵커가 길면 앞부분 40자만 비교 (30 -> 40으로 확대)
                        compare_anchor = anchor[:40]
                        s = difflib.SequenceMatcher(None, search_region, compare_anchor)
                        match = s.find_longest_match(0, len(search_region), 0, len(compare_anchor))
                        
                        # 매칭된 길이가 10자 이상이면 인정 (15 -> 10으로 완화)
                        if match.size >= 10:
                            idx = search_start + match.a
                            print(f"    [Fuzzy Match] 퍼지 매칭 성공({match.size}자): '{search_region[match.a:match.a+15]}...'")

                # ---------------------------------------------------------
                # E. 공통 중복 체크 (Common Duplicate Check)
                # 어떤 방식(A,B,C,D)으로든 앵커(idx)를 찾았을 때,
                # 그것이 TOC(목차)이고 뒤에 본문이 따로 있는지 확인
                # ---------------------------------------------------------
                if idx != -1 and idx < 8000:
                    # Duplicate Check Logic (Moved from Block A)
                    
                    # 검색 시작 위치: 현재 찾은 idx + 앵커길이(혹은 20자)
                    # 앵커가 정확하지 않을 수 있으므로 대략적으로 잡음
                    check_start = idx + 20 
                    check_limit = min(check_start + 25000, len(text))
                    search_region = text[check_start : check_limit]
                    
                    # Seed 변형 생성
                    raw_seed = anchor[:10]
                    clean_seed = re.sub(r'[^\w\s]', '', raw_seed).strip()
                    seeds = [raw_seed, clean_seed]
                    
                    found_dup = False
                    for seed in seeds:
                        if len(seed) < 2: continue
                        
                        try:
                            # 모든 공백을 유연하게 처리 (\s+)
                            parts = seed.split()
                            if not parts: continue
                            
                            seed_p = r'\s+'.join(re.escape(p) for p in parts)
                            
                            seed_re = re.compile(seed_p, re.IGNORECASE)
                            seed_match = seed_re.search(search_region)
                            
                            if seed_match:
                                # 재등장 확인됨 -> 현재 idx는 TOC일 확률 높음
                                seed_pos = seed_match.start()
                                real_second_idx = check_start + seed_pos
                                print(f"    [Merge/Global] 중복 앵커 감지 (Regex): {idx} vs ~{real_second_idx}. 본문(후방) 앵커 선택.")
                                idx = real_second_idx 
                                found_dup = True
                                break
                        except Exception as re_err:
                            print(f"    [Warning] 중복 체크 Regex 오류: {re_err}")
                            continue

                if idx != -1:
                    start_indices.append(idx)
                    last_idx = idx
                else:
                    clean_display = anchor.replace('\n', ' ')[:50]
                    print(f"[Warning] 앵커 찾기 실패 (통합됨): '{clean_display}...'")

            # 2. 인덱스 기반으로 자르기
            if not start_indices:
                return [text]
            
            # 첫 번째 씬이 0부터 시작하지 않으면 강제로 0 추가
            if start_indices[0] != 0:
                start_indices.insert(0, 0)
                
            for i in range(len(start_indices)):
                start = start_indices[i]
                end = start_indices[i+1] if i + 1 < len(start_indices) else len(text)
                
                scene_content = text[start:end].strip()
                if scene_content:
                    scenes.append(scene_content)
            
            print(f"[OK] LLM 씬 분할 완료: {len(scenes)}개 씬 생성")
            
            # 3. 후처리: 너무 짧은 씬(TOC 항목 등)을 이전 씬에 병합
            merged_scenes = []
            if not scenes:
                return [text]

            current_chunk = scenes[0]
            
            # 챕터 패턴 (재사용)
            check_patterns = [
                r'^제\s*\d+\s*장', r'^\d+\s*장\.', r'^Chapter\s+\d+', r'^CHAPTER\s+\d+',
                r'^[IVX]{1,8}\s*$', r'^[IVXLCDM]{1,10}\s*$', r'^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\s*$',
                r'^[IVX]{1,8}\.\s+', r'^[IVXLCDM]{1,10}\.\s+',
                r'^나\s*$', r'^다\s*$', r'^라\s*$', r'^뷔\s*$', r'^[1-9]\s*$',
                r'^에필로그', r'^Epilogue', r'^EPILOGUE', r'^#\s+', r'^##\s+'
            ]
            
            for i in range(1, len(scenes)):
                next_scene = scenes[i]
                
                # 병합 조건 검사
                # 1. 길이가 너무 짧음 (< 300자)
                is_short = len(next_scene) < 300
                
                # 2. 챕터 헤더만 있는 경우 체크 (< 500자 이면서 헤더 패턴 매칭)
                is_header_only = False
                if len(next_scene) < 500:
                    first_line = next_scene.strip().split('\n')[0]
                    is_header_only = any(re.match(p, first_line, re.IGNORECASE) for p in check_patterns)
                
                # 3. 줄 수가 너무 적음 (< 5줄)
                lines_count = len(next_scene.strip().split('\n'))
                is_few_lines = lines_count <= 5
                
                should_merge = (is_short and is_few_lines) or is_header_only
                
                if should_merge:
                    print(f"    [Post-Merge] 씬 {i+1}이 너무 짧음({len(next_scene)}자). 이전 씬에 병합합니다.")
                    current_chunk += "\n\n" + next_scene
                else:
                    merged_scenes.append(current_chunk)
                    current_chunk = next_scene
            
            # 마지막 청크 추가
            merged_scenes.append(current_chunk)
            
            print(f"[OK] 씬 병합 완료: {len(scenes)} -> {len(merged_scenes)}개")
            return merged_scenes

        except Exception as e:
            print(f"[Error] LLM 씬 분할 실패: {e}")
            return [text]

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
            
            # 타입 체크: 리스트가 반환된 경우 처리
            if isinstance(data, list):
                print(f"[Warning] 씬 {scene_index}: API가 리스트를 반환했습니다. 첫 번째 항목 사용")
                if len(data) > 0 and isinstance(data[0], dict):
                    data = data[0]
                else:
                    raise ValueError("유효하지 않은 응답 형식")
            
            # 딕셔너리가 아닌 경우 에러
            if not isinstance(data, dict):
                raise ValueError(f"예상치 못한 응답 타입: {type(data)}")
            
            return StructuredScene(
                scene_index=scene_index,
                original_text=scene_text,
                summary=data.get('summary', ''),
                characters=data.get('characters', []),
                relationships=data.get('relationships', []),
                locations=data.get('locations', []),
                items=data.get('items', []),
                key_events=data.get('key_events', []),
                mood=data.get('mood', ''),
                time_period=data.get('time_period')
            )

        except Exception as e:
            print(f"[Warning] 씬 {scene_index} 구조화 실패: {e}")
            # 실패 시 기본 객체 반환
            return StructuredScene(
                scene_index=scene_index,
                original_text=scene_text,
                summary="분석 실패",
                characters=[],
                relationships=[],
                locations=[],
                items=[],
                key_events=[],
                mood="",
                time_period=None
            )
    
    def _extract_global_entities_batched(
        self,
        scenes_summary: List[Dict],
        full_scenes_data: List[Dict],
        custom_system_prompt: Optional[str],
        batch_size: int
    ) -> Dict:
        """씬을 배치로 나누어 전역 엔티티 추출 후 병합"""
        
        num_batches = (len(scenes_summary) + batch_size - 1) // batch_size
        print(f"[Batch] 총 {num_batches}개 배치로 처리합니다.")
        
        # 각 배치별 결과 저장
        all_characters = {}  # name을 키로 사용
        all_items = {}
        all_locations = {}
        all_key_events = []
        
        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, len(scenes_summary))
            batch_scenes = scenes_summary[start_idx:end_idx]
            
            print(f"  배치 {batch_idx + 1}/{num_batches}: 씬 {start_idx}~{end_idx-1} 분석 중...")
            
            # 배치 분석
            batch_info = {"scenes": batch_scenes}
            
            if custom_system_prompt:
                prompt = f"""{custom_system_prompt}

다음은 소설의 씬 분석 데이터입니다. 이 데이터를 바탕으로 위 프롬프트의 지시사항을 수행하여 JSON 형식으로 응답하세요:

{json.dumps(batch_info, ensure_ascii=False, indent=2)}
"""
            else:
                prompt = f"""{self.system_prompt}

다음은 여러 씬의 분석 결과입니다. 전체 스토리에서 등장하는 주요 엔티티들을 통합하여 정리하세요:

{json.dumps(batch_info, ensure_ascii=False, indent=2)}

다음 형식의 JSON으로 응답하세요:

{{
  "characters": [
    {{
      "name": "인물 이름",
      "aliases": ["별칭1", "별칭2"],
      "description": "인물 설명",
      "visual_description": "외모 묘사 (머리색, 눈 색, 체형, 복장, 나이대, 인상 등 시각적 특징)",
      "first_appearance": 첫_등장_씬_번호,
      "traits": ["특징1", "특징2"]
    }}
  ],
  "items": [
    {{
      "name": "아이템 이름",
      "description": "설명",
      "visual_description": "아이템의 시각적 묘사 (재질, 색상, 크기, 형태, 장식 등)",
      "first_appearance": 첫_등장_씬_번호,
      "significance": "스토리상 의미"
    }}
  ],
  "locations": [
    {{
      "name": "장소 이름",
      "description": "장소 설명",
      "visual_description": "장소의 시각적 묘사 (건축 양식, 분위기, 조명, 색감, 크기 등)",
      "scenes": [등장한_씬_번호들]
    }}
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
                
                try:
                    batch_result = json.loads(json_text)
                except json.JSONDecodeError as json_err:
                    print(f"    [Warning] 배치 {batch_idx + 1} JSON 파싱 실패, 부분 복구 시도...")
                    last_brace = json_text.rfind('}')
                    if last_brace > 0:
                        truncated_json = json_text[:last_brace + 1]
                        try:
                            batch_result = json.loads(truncated_json)
                            print("    [Info] 부분 복구 성공")
                        except json.JSONDecodeError:
                            print("    [Error] 복구 실패, 배치 건너뜀")
                            continue
                    else:
                        print("    [Error] 복구 실패, 배치 건너뜀")
                        continue
                
                # 결과 병합
                for char in batch_result.get('characters', []):
                    name = char.get('name')
                    if name and name not in all_characters:
                        all_characters[name] = char
                
                for item in batch_result.get('items', []):
                    name = item.get('name')
                    if name and name not in all_items:
                        all_items[name] = item
                
                for loc in batch_result.get('locations', []):
                    name = loc.get('name')
                    if name and name not in all_locations:
                        all_locations[name] = loc
                
                all_key_events.extend(batch_result.get('key_events', []))
                
                print(f"    [Done] 배치 {batch_idx + 1} 완료")
                
            except Exception as e:
                print(f"    [Warning] 배치 {batch_idx + 1} 처리 실패: {e}")
                continue
        
        # 최종 결과 구성
        result = {
            "characters": list(all_characters.values()),
            "items": list(all_items.values()),
            "locations": list(all_locations.values()),
            "key_events": all_key_events,
            "scenes": full_scenes_data
        }
        
        print(f"[OK] 배치 처리 완료: {len(result['characters'])}명, {len(result['items'])}개 아이템, {len(result['locations'])}개 장소")
        
        return result
            
    def _repair_json(self, json_text: str) -> str:
        """망가진 JSON 문자열을 복구 시도"""
        # 1. 제어 문자 제거 (줄바꿈/탭 제외)
        json_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_text)
        
        # 2. 따옴표 내부의 줄바꿈을 \n으로 변경 (파이썬 json.loads는 멀티라인 문자열을 싫어함)
        # (매우 복잡한 정규식 대신, 간단한 복구만 수행)
        
        # 3. 콤마 누락 복구 (객체/배열 끝의 콤마 등)
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
        
        return json_text

    @staticmethod
    def _normalize_character_name(name: str) -> str:
        """경칭/호칭 접미사를 제거하여 인물 이름 정규화.
        예: "어터슨 씨" → "어터슨", "Mr. Hyde" → "Hyde", "김 박사" → "김"
        """
        if not name or not isinstance(name, str):
            return name
        name = name.strip()
        # 한국어 경칭 접미사 (긴 것부터 매칭)
        kr_suffixes = ['선생님', '교수님', '박사님', '사장님', '부장님', '과장님',
                       '선생', '교수', '박사', '사장', '부장', '과장',
                       '씨', '님', '군', '양']
        for suffix in kr_suffixes:
            if name.endswith(' ' + suffix):
                name = name[:-len(suffix) - 1].strip()
                break
            elif name.endswith(suffix) and len(name) > len(suffix):
                name = name[:-len(suffix)].strip()
                break
        # 영문 경칭 접두사
        en_titles = ['Mr.', 'Ms.', 'Mrs.', 'Miss', 'Dr.', 'Prof.', 'Sir', 'Madam', 'Lord', 'Lady']
        for title in en_titles:
            if name.startswith(title + ' ') and len(name) > len(title) + 1:
                name = name[len(title) + 1:].strip()
                break
        return name

    def extract_global_entities(
        self,
        structured_scenes: List[StructuredScene],
        custom_system_prompt: Optional[str] = None
    ) -> Dict:
        """
        [최적화됨] 별도의 Gemini 호출 없이, 각 씬에서 추출된 정보를 통합(Aggregation)하여 전역 엔티티 생성.
        - 속도: 즉시 완료 (LLM 호출 제거)
        - 안정성: JSON 파싱 오류 원천 차단
        """
        print("[Aggregation] 전역 엔티티 통합(Aggregation) 시작 (LLM 호출 생략)...")
        
        all_characters = {}
        all_items = {}
        all_locations = {}
        all_key_events = []
        all_relationships = {}  # (source, target) → relationship dict

        # 원본 씬 데이터도 결과에 포함 (프론트엔드 요구사항)
        full_scenes_data = []

        for scene in structured_scenes:
            idx = scene.scene_index
            scene_data = asdict(scene)
            if 'original_text' in scene_data:
                del scene_data['original_text']
            full_scenes_data.append(scene_data)
            
            # 1. Characters 통합
            for char in scene.characters:
                # 하위 호환성: 문자열이면 객체로 변환
                if isinstance(char, str):
                    raw_name = char
                    desc = ""
                    visual_desc = ""
                    traits = []
                else:
                    raw_name = char.get('name') or 'Unknown'
                    desc = char.get('description') or ''
                    visual_desc = char.get('visual_description') or ''
                    traits = char.get('traits') or []

                name = self._normalize_character_name(raw_name)
                if name not in all_characters:
                    all_characters[name] = {
                        "name": name,
                        "description": desc,
                        "visual_description": visual_desc,
                        "aliases": [],
                        "traits": [],
                        "appearances": []
                    }
                # 설명이 더 길면 업데이트 (정보 보강) - trait도 합집합
                if len(desc) > len(all_characters[name]['description']):
                    all_characters[name]['description'] = desc
                
                # visual_description도 더 길면 업데이트
                if len(visual_desc) > len(all_characters[name].get('visual_description', '')):
                    all_characters[name]['visual_description'] = visual_desc
                
                # Traits 통합 (중복 제거)
                if traits:
                     for t in traits:
                         if t not in all_characters[name]['traits']:
                             all_characters[name]['traits'].append(t)
                
                if idx not in all_characters[name]['appearances']:
                    all_characters[name]['appearances'].append(idx)

            # 2. Items 통합
            for item in scene.items:
                if isinstance(item, str):
                    name = item
                    desc = ""
                    visual_desc = ""
                else:
                    name = item.get('name') or 'Unknown'
                    desc = item.get('description') or ''
                    visual_desc = item.get('visual_description') or ''

                if name not in all_items:
                    all_items[name] = {
                        "name": name,
                        "description": desc,
                        "visual_description": visual_desc,
                        "first_appearance": idx,
                        "significance": "",
                        "appearances": []
                    }
                # 설명이 더 길면 업데이트
                if len(desc) > len(all_items[name]['description']):
                    all_items[name]['description'] = desc
                
                # visual_description도 더 길면 업데이트
                if len(visual_desc) > len(all_items[name].get('visual_description', '')):
                    all_items[name]['visual_description'] = visual_desc
                
                if idx not in all_items[name]['appearances']:
                    all_items[name]['appearances'].append(idx)

            # 3. Locations 통합
            for loc in scene.locations:
                if isinstance(loc, str):
                    name = loc
                    desc = ""
                    visual_desc = ""
                else:
                    name = loc.get('name') or 'Unknown'
                    desc = loc.get('description') or ''
                    visual_desc = loc.get('visual_description') or ''

                if name not in all_locations:
                    all_locations[name] = {
                        "name": name,
                        "description": desc,
                        "visual_description": visual_desc,
                        "scenes": []
                    }
                # 설명이 더 길면 업데이트
                if len(desc) > len(all_locations[name]['description']):
                    all_locations[name]['description'] = desc
                
                # visual_description도 더 길면 업데이트
                if len(visual_desc) > len(all_locations[name].get('visual_description', '')):
                    all_locations[name]['visual_description'] = visual_desc
                
                if idx not in all_locations[name]['scenes']:
                    all_locations[name]['scenes'].append(idx)
            
            # 4. Relationships 통합
            for rel in getattr(scene, 'relationships', []) or []:
                if isinstance(rel, dict):
                    src = self._normalize_character_name(rel.get('source', ''))
                    tgt = self._normalize_character_name(rel.get('target', ''))
                    if src and tgt:
                        key = tuple(sorted([src, tgt]))
                        desc = rel.get('description', '')
                        relation = rel.get('relation', '')
                        if key not in all_relationships:
                            all_relationships[key] = {
                                "character1": key[0],
                                "character2": key[1],
                                "relation": relation,
                                "description": desc,
                                "scenes": []
                            }
                        if len(desc) > len(all_relationships[key]['description']):
                            all_relationships[key]['description'] = desc
                        if relation and len(relation) > len(all_relationships[key].get('relation', '')):
                            all_relationships[key]['relation'] = relation
                        if idx not in all_relationships[key]['scenes']:
                            all_relationships[key]['scenes'].append(idx)

            # 5. Key Events 통합
            for event in scene.key_events:
                if isinstance(event, str):
                    summary = event
                    importance = "중"
                else:
                    summary = event.get('summary') or ''
                    importance = event.get('importance') or '중'
                
                all_key_events.append({
                    "summary": summary,
                    "scene_index": idx,
                    "importance": importance
                })

        # 결과 포맷팅 (리스트 변환 & 정렬)
        
        # Characters: 등장 횟수 순 정렬
        final_chars = list(all_characters.values())
        for char in final_chars:
            char['appearances'].sort()
            char['first_appearance'] = char['appearances'][0] if char['appearances'] else 0
            char['appearance_count'] = len(char['appearances'])
        final_chars.sort(key=lambda x: x['appearance_count'], reverse=True)

        # Items: 등장 횟수 순 정렬
        final_items = list(all_items.values())
        for item in final_items:
            item['appearances'].sort()
            item['first_appearance'] = item['appearances'][0] if item['appearances'] else 0
            item['appearance_count'] = len(item['appearances'])
        final_items.sort(key=lambda x: x['appearance_count'], reverse=True)
        
        # Locations: 등장 횟수 순 정렬
        final_locations = list(all_locations.values())
        for loc in final_locations:
            loc['scenes'].sort()
            loc['first_appearance'] = loc['scenes'][0] if loc['scenes'] else 0
            loc['appearance_count'] = len(loc['scenes'])
        final_locations.sort(key=lambda x: x['appearance_count'], reverse=True)

        # Relationships: 등장 횟수 순 정렬
        final_relationships = sorted(
            all_relationships.values(),
            key=lambda x: len(x.get('scenes', [])),
            reverse=True
        )

        return {
            "characters": final_chars,
            "items": final_items,
            "locations": final_locations,
            "key_events": all_key_events,
            "relationships": final_relationships,
            "scenes": full_scenes_data
        }

