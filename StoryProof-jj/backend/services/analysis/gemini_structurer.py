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
    characters: List[str]
    locations: List[str]
    items: List[str]
    key_events: List[str]
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
        self.model_name = 'gemini-2.5-flash'
        
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
            from google.genai import types
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json'  # JSON 응답 강제
                )
            )
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
            
    def extract_global_entities(
        self,
        structured_scenes: List[StructuredScene],
        custom_system_prompt: Optional[str] = None
    ) -> Dict:
        """전체 씬에서 등장하는 엔티티 통합 분석 (커스텀 프롬프트 지원)"""
        
        # 모든 씬 정보 수집 (원본 텍스트 제외하여 토큰 절약)
        scenes_summary = []
        full_scenes_data = []  # 반환용 전체 데이터 (text 포함)

        for scene in structured_scenes:
            scene_data = asdict(scene)
            full_scenes_data.append(scene_data.copy())  # 원본 보존

            if 'original_text' in scene_data:
                del scene_data['original_text']  # 프롬프트용에서는 제거
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
                        if loc_name in scene_locs:
                            related_scenes.append(scene['scene_index'])
                    
                    loc['scenes'] = related_scenes
                    loc['appearance_count'] = len(related_scenes)
            
            return result
        
        except Exception as e:
            print(f"⚠️ 전역 엔티티 추출 실패: {e}")
            return {"scenes": full_scenes_data}
