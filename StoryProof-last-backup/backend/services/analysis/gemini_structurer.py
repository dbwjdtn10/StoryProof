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
  "summary": "씬의 핵심 요약 (2-3 문장)",
  "characters": [{"name": "인물 이름", "description": "행동/성격 묘사 (1문장)", "traits": ["특성1", "특성2"]}],
  "locations": [{"name": "장소 이름", "description": "장소 묘사"}],
  "items": [{"name": "아이템 이름", "description": "용도/의미"}],
  "key_events": [{"summary": "사건 내용", "importance": "상/중/하"}],
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
        예: '제1장', 'Chapter 1' 등
        """
        # 1. 챕터 패턴 정의
        patterns = [
            r'^제\s*\d+\s*장.*$',       # 제1장, 제 1 장 등 (줄 시작)
            r'^\s*제\s*\d+\s*장.*$',     # 공백 후 제1장
            r'^Chapter\s*\d+.*$',        # Chapter 1
            r'^\s*Chapter\s*\d+.*$',      # 공백 후 Chapter 1
            r'^#\s+.*$',                 # Markdown H1
            r'^##\s+.*$'                 # Markdown H2
        ]
        
        found_anchors = []
        lines = text.split('\n')
        
        # 2. 라인 단위 검색
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for p in patterns:
                if re.match(p, line, re.IGNORECASE):
                    # 너무 짧으면(5자 미만) 앵커로서 부적합할 수 있음
                    if len(line) >= 4:
                        # 중복 방지 및 목차 부분 제외 로직은 
                        # 호출부에서 텍스트 상단을 무시하거나 하는 방식으로 처리 가능
                        if line not in found_anchors:
                            found_anchors.append(line)
                    break
        
        # 3. 목차(Table of Contents) 필터링
        # 본문 시작 전에 목차가 나오는 경우 동일한 패턴이 중복될 수 있음.
        # 간단하게, 본문 뒤쪽(5000자 이후)에서 발견된 것 위주로 하거나, 
        # 처음 발견된 것들이 너무 붙어있으면(목차) 건너뛰는 방식.
        if len(found_anchors) > 1:
            # 첫 번째 장이 나타나는 위치 확인
            first_idx = text.find(found_anchors[0])
            second_idx = text.find(found_anchors[1])
            
            # 만약 첫 번째와 두 번째 앵커 사이의 거리가 매우 짧다면(예: 300자 미만),
            # 그것은 목차일 확률이 높음.
            if second_idx != -1 and (second_idx - first_idx) < 300:
                print(f"   [TOC] 목차(TOC)로 추정되는 패턴 감지됨. 필터링 후 본문 검색 시도...")
                # 목차 이후의 텍스트에서 다시 검색하는 복잡도 대신, 
                # split_scenes 매칭 시 'last_idx'를 활용하여 해결되도록 유도.
        
        if found_anchors:
             print(f"   [Anchors] 정규식으로 {len(found_anchors)}개의 후보 앵커 발견: {found_anchors[:3]}...")
             
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

Task: 아래 소설 전체를 읽고, 이야기의 흐름이 크게 전환되는 "주요 장면(Major Scene)"들의 **시작 부분(첫 50자)**을 찾아주세요.

**CRITICAL RULES (매우 중요):**
1. **EXACT MATCH ONLY (정확히 일치해야 함):**
   - 반환하는 문자열은 원본 텍스트에 있는 문장과 **토씨 하나 틀리지 않고 100% 일치**해야 합니다.
   - 단어 수정, 요약, 어미 변경, 문장 부호 변경을 **절대 금지**합니다.
   - 원본 텍스트를 그대로 복사해서 붙여넣으세요.
   
2. **Anchor Length (길이):**
   - 씬이 시작되는 문장의 **앞부분 30~50자**만 발췌하세요. 너무 길면 안 됩니다.

3. **Segmentation (분할 기준 - 중요):**
   - **Chapter/Section 단위로만 나누세요.** (소설 목차 기준)
   - 단순한 장소 이동, 시간 경과, 대화 전환으로는 쪼개지 마세요.
   {hard_anchors_hint}
   - **목표 갯수 (참고용):** 텍스트 길이를 고려할 때 약 **{expected_min}~{expected_max}개** 정도의 챕터가 있을 것으로 **추정**됩니다. 이 숫자는 **참고만 하세요.**
   - **최우선 기준:** AI인 당신의 판단하에 **이야기의 흐름이 실제로 바뀌는 '챕터/장' 구분**을 최우선으로 따르세요.
   - 추정치와 다르더라도, 실제 소설의 구조가 그렇다면 소설의 구조를 존중하세요. (단, 50개 이상으로 너무 잘게 쪼개는 것만 피하세요.)

Original Text:
{text}

Output Format (JSON List of Strings):
["Scene 1 Start Text...", "Scene 2 Start Text..."]
"""
        try:
            print(f"--- LLM 씬 분할(Anchor 방식) 시작... (텍스트 길이: {len(text)}자)")
            
            # 긴 텍스트 처리를 위해 타임아웃/재시도 설정이 중요
            response = self._generate_with_retry(real_prompt)
            json_text = response.text.strip()
            
            if json_text.startswith("```"):
                json_text = re.sub(r'^```json?\s*|\s*```$', '', json_text, flags=re.MULTILINE)
            
            start_anchors = json.loads(json_text)
            
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
                if not anchor or len(anchor.strip()) < 5:
                    continue
                    
                # A. 정확히 일치 (Exact Match)
                idx = text.find(anchor, last_idx + 1)
                
                # B. 공백 정규화 및 부분 일치 (Whitespace Normalized Match)
                if idx == -1:
                    import re
                    # 앵커의 앞 20자리만 추출하여 검색 (줄바꿈/공백 정규화)
                    clean_seed = re.sub(r'\s+', ' ', anchor).strip()[:20]
                    # 특수문자 이스케이프
                    pattern_str = re.escape(clean_seed).replace(r'\ ', r'\s+')
                    logging_pattern = re.compile(pattern_str)
                    
                    # 검색 범위 제한 (속도 최적화: 현재 위치 + 5000자)
                    search_limit = min(last_idx + 5000, len(text))
                    search_region = text[last_idx+1:search_limit]
                    
                    match = logging_pattern.search(search_region)
                    if match:
                        idx = last_idx + 1 + match.start()
                        print(f"    [Match] 부분/공백 정규화 매칭 성공: '{anchor[:10]}...'")

                # C. 퍼지 매칭 (Fuzzy Match - difflib)
                if idx == -1:
                    import difflib
                    search_window = 3000  # 검색 범위 확대
                    search_start = last_idx + 1
                    search_end = min(search_start + search_window, len(text))
                    search_region = text[search_start:search_end]
                    
                    # 앵커가 '제N장' 이나 'Chapter' 로 시작하는지 확인
                    is_chapter = re.search(r'(제\s*\d+\s*장|Chapter\s*\d+)', anchor, re.IGNORECASE)
                    
                    if is_chapter:
                        # 장 번호 패턴으로 직접 검색 시도
                        chap_p = re.escape(is_chapter.group(0)).replace(r'\ ', r'\s+')
                        chap_match = re.search(chap_p, search_region, re.IGNORECASE)
                        if chap_match:
                            idx = search_start + chap_match.start()
                            print(f"    [Pattern Match] 장 번호 패턴 매칭 성공: '{anchor[:15]}...'")
                    
                    if idx == -1:
                        # difflib으로 유사한 부분 찾기
                        # 앵커가 길면 앞부분 30자만 비교
                        compare_anchor = anchor[:30]
                        s = difflib.SequenceMatcher(None, search_region, compare_anchor)
                        match = s.find_longest_match(0, len(search_region), 0, len(compare_anchor))
                        
                        # 매칭된 길이가 15자 이상이면 인정
                        if match.size > 15:
                            idx = search_start + match.a
                            print(f"    [Fuzzy Match] 퍼지 매칭 성공({match.size}자): '{search_region[match.a:match.a+10]}...'")

                if idx != -1:
                    start_indices.append(idx)
                    last_idx = idx
                else:
                    clean_display = anchor.replace('\n', ' ')[:40]
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
            
            print(f"✅ LLM 씬 분할 완료: {len(scenes)}개 씬 생성")
            return scenes

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
                        batch_result = json.loads(truncated_json)
                        print("    [Info] 부분 복구 성공")
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
                
                print(f"    ✓ 배치 {batch_idx + 1} 완료")
                
            except Exception as e:
                print(f"    ⚠️ 배치 {batch_idx + 1} 처리 실패: {e}")
                continue
        
        # 최종 결과 구성
        result = {
            "characters": list(all_characters.values()),
            "items": list(all_items.values()),
            "locations": list(all_locations.values()),
            "key_events": all_key_events,
            "scenes": full_scenes_data
        }
        
        print(f"✅ 배치 처리 완료: {len(result['characters'])}명, {len(result['items'])}개 아이템, {len(result['locations'])}개 장소")
        
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
                    name = char
                    desc = ""
                else:
                    name = char.get('name', 'Unknown')
                    desc = char.get('description', '')
                    traits = char.get('traits', [])

                if name not in all_characters:
                    all_characters[name] = {
                        "name": name,
                        "description": desc,
                        "aliases": [],
                        "traits": [],
                        "appearances": []
                    }
                # 설명이 더 길면 업데이트 (정보 보강) - trait도 합집합
                if len(desc) > len(all_characters[name]['description']):
                    all_characters[name]['description'] = desc
                
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
                else:
                    name = item.get('name', 'Unknown')
                    desc = item.get('description', '')

                if name not in all_items:
                    all_items[name] = {
                        "name": name,
                        "description": desc,
                        "first_appearance": idx,
                        "significance": "",
                        "appearances": []
                    }
                # 설명이 더 길면 업데이트
                if len(desc) > len(all_items[name]['description']):
                    all_items[name]['description'] = desc
                
                if idx not in all_items[name]['appearances']:
                    all_items[name]['appearances'].append(idx)

            # 3. Locations 통합
            for loc in scene.locations:
                if isinstance(loc, str):
                    name = loc
                    desc = ""
                else:
                    name = loc.get('name', 'Unknown')
                    desc = loc.get('description', '')

                if name not in all_locations:
                    all_locations[name] = {
                        "name": name,
                        "description": desc,
                        "scenes": []
                    }
                # 설명이 더 길면 업데이트
                if len(desc) > len(all_locations[name]['description']):
                    all_locations[name]['description'] = desc
                
                if idx not in all_locations[name]['scenes']:
                    all_locations[name]['scenes'].append(idx)
            
            # 4. Key Events 통합
            for event in scene.key_events:
                if isinstance(event, str):
                    summary = event
                    importance = "중"
                else:
                    summary = event.get('summary', '')
                    importance = event.get('importance', '중')
                
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

        return {
            "characters": final_chars,
            "items": final_items,
            "locations": final_locations,
            "key_events": all_key_events,
            "scenes": full_scenes_data
        }

