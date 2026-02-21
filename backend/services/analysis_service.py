"""
분석 서비스 모듈

소설 챕터의 스토리보드 바이블 데이터를 조회하고 관리하는 서비스입니다.
인물, 장소, 아이템, 주요 사건 등의 분석 데이터를 제공합니다.
"""

import time
import threading
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import logging

from backend.db.models import Novel, Chapter, Analysis, AnalysisType, VectorDocument

# 로거 설정
logger = logging.getLogger(__name__)

# Bible summary TTL 캐시 (키: (novel_id, chapter_id), 값: (summary_str, timestamp))
_bible_summary_cache: Dict[tuple, tuple] = {}
_bible_summary_lock = threading.Lock()
_BIBLE_SUMMARY_TTL = 300  # 5분
_BIBLE_SUMMARY_MAX_SIZE = 200  # 캐시 최대 항목 수


class AnalysisService:
    """소설 분석 데이터 관리 서비스"""

    @staticmethod
    def _entity_name(entity, key: str = 'name'):
        """딕셔너리 또는 문자열 엔티티에서 필드값 추출."""
        return entity.get(key) if isinstance(entity, dict) else entity

    @staticmethod
    def get_chapter_bible(
        db: Session, 
        novel_id: int, 
        chapter_id: int, 
        user_id: int, 
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        회차의 스토리보드 바이블 데이터 조회
        
        Args:
            db: 데이터베이스 세션
            novel_id: 소설 ID
            chapter_id: 챕터 ID
            user_id: 사용자 ID
            is_admin: 관리자 권한 여부
            
        Returns:
            Dict[str, Any]: 인물, 장소, 아이템, 주요 사건 등을 포함한 바이블 데이터
            
        Raises:
            HTTPException: 소설/챕터를 찾을 수 없거나 권한이 없는 경우
        """
        try:
            # 1. 소설 존재 여부 및 권한 확인
            novel = db.query(Novel).filter(Novel.id == novel_id).first()
            if not novel:
                logger.warning(f"Novel not found: novel_id={novel_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="소설을 찾을 수 없습니다."
                )
            
            # 권한 검증: 작성자, 관리자, 또는 공개 소설인 경우만 접근 가능
            if novel.author_id != user_id and not is_admin and not novel.is_public:
                logger.warning(
                    f"Unauthorized access attempt: user_id={user_id}, novel_id={novel_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="권한이 없습니다."
                )
            
            # 2. 챕터 존재 여부 확인
            chapter = db.query(Chapter).filter(
                Chapter.id == chapter_id,
                Chapter.novel_id == novel_id
            ).first()
            
            if not chapter:
                logger.warning(
                    f"Chapter not found: chapter_id={chapter_id}, novel_id={novel_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="회차를 찾을 수 없습니다."
                )
            
            # 3. 분석 데이터 조회
            analysis_record = db.query(Analysis).filter(
                Analysis.chapter_id == chapter_id,
                Analysis.analysis_type == AnalysisType.CHARACTER
            ).first()
            
            # 3-1. 기존 분석 결과가 있는 경우 - 통계 보강 후 반환
            if analysis_record and analysis_record.result:
                return AnalysisService._enrich_analysis_result(
                    db, novel_id, chapter_id, analysis_record.result
                )
            
            # 3-2. 분석 결과가 없는 경우 - VectorDocument 기반 실시간 집계
            logger.info(
                f"No analysis found, generating from VectorDocuments: chapter_id={chapter_id}"
            )
            return AnalysisService._generate_bible_from_vectors(
                db, novel_id, chapter_id
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error in get_chapter_bible: novel_id={novel_id}, "
                f"chapter_id={chapter_id}, error={str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="바이블 데이터 조회 중 오류가 발생했습니다."
            )
    
    @staticmethod
    def _enrich_analysis_result(
        db: Session, 
        novel_id: int, 
        chapter_id: int, 
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        기존 분석 결과에 통계 및 씬 데이터 보강
        
        Args:
            db: 데이터베이스 세션
            novel_id: 소설 ID
            chapter_id: 챕터 ID
            result: 기존 분석 결과
            
        Returns:
            Dict[str, Any]: 보강된 분석 결과
        """
        # VectorDocument에서 씬 데이터 조회
        scenes = db.query(VectorDocument).filter(
            VectorDocument.novel_id == novel_id,
            VectorDocument.chapter_id == chapter_id
        ).order_by(VectorDocument.chunk_index).all()
        
        # 인물별 등장 통계 계산
        character_stats: Dict[str, Dict[str, Any]] = {}
        for scene in scenes:
            metadata = scene.metadata_json or {}
            for char in metadata.get('characters', []):
                char_name = AnalysisService._entity_name(char)
                    
                if char_name:
                    if char_name not in character_stats:
                        character_stats[char_name] = {'count': 0, 'appearances': []}
                    character_stats[char_name]['count'] += 1
                    character_stats[char_name]['appearances'].append(scene.chunk_index)
        
        # 분석 결과에 통계 정보 추가
        if 'characters' in result:
            for char in result['characters']:
                name = char.get('name')
                if name and name in character_stats:
                    char['appearance_count'] = character_stats[name]['count']
                    char['appearances'] = character_stats[name]['appearances']
                else:
                    # 통계가 없는 경우 기본값 설정
                    if 'appearance_count' not in char:
                        char['appearance_count'] = 1
                    if 'appearances' not in char:
                        char['appearances'] = [char.get('first_appearance', 0)]
        
        # 씬 데이터 추가 (프론트엔드 파티션 렌더링용)
        result['scenes'] = [
            {
                'scene_index': s.chunk_index,
                'original_text': s.chunk_text,
                'summary': (s.metadata_json or {}).get('summary', '')
            } for s in scenes
        ]
        result['chapter_id'] = chapter_id
        
        return result
    
    @staticmethod
    def _generate_bible_from_vectors(
        db: Session, 
        novel_id: int, 
        chapter_id: int
    ) -> Dict[str, Any]:
        """
        VectorDocument 기반 실시간 바이블 데이터 생성
        
        분석 결과가 없는 경우 VectorDocument의 메타데이터를 집계하여
        바이블 데이터를 실시간으로 생성합니다.
        
        Args:
            db: 데이터베이스 세션
            novel_id: 소설 ID
            chapter_id: 챕터 ID
            
        Returns:
            Dict[str, Any]: 생성된 바이블 데이터
        """
        # VectorDocument에서 씬 데이터 조회
        scenes = db.query(VectorDocument).filter(
            VectorDocument.novel_id == novel_id,
            VectorDocument.chapter_id == chapter_id
        ).order_by(VectorDocument.chunk_index).all()
        
        # 바이블 데이터 초기화
        bible_data: Dict[str, Any] = {
            "characters": [],
            "locations": [],
            "items": [],
            "key_events": [],
            "timeline": [],
            "scenes": [],
            "chapter_id": chapter_id
        }
        
        # 씬 데이터 추가
        bible_data['scenes'] = [
            {
                'scene_index': s.chunk_index,
                'original_text': s.chunk_text,
                'summary': (s.metadata_json or {}).get('summary', '') or (s.chunk_text[:100] + "...")
            } for s in scenes
        ]
        
        # 집계용 딕셔너리
        character_dict: Dict[str, Dict[str, Any]] = {}
        location_dict: Dict[str, Dict[str, Any]] = {}
        item_dict: Dict[str, Dict[str, Any]] = {}
        
        # 각 씬의 메타데이터에서 정보 추출 및 집계
        for scene in scenes:
            metadata = scene.metadata_json or {}
            
            # 인물 정보 추출 및 집계
            for char in metadata.get('characters', []):
                char_name = AnalysisService._entity_name(char)
                if char_name and char_name not in character_dict:
                    character_dict[char_name] = {
                        'name': char_name,
                        'first_appearance': scene.chunk_index,
                        'appearances': [scene.chunk_index],
                        'description': char.get('description', '') if isinstance(char, dict) else '',
                        'traits': char.get('traits', []) if isinstance(char, dict) else []
                    }
                elif char_name:
                    # 기존 인물의 추가 등장 기록
                    if scene.chunk_index not in character_dict[char_name]['appearances']:
                        character_dict[char_name]['appearances'].append(scene.chunk_index)
                    
                    if isinstance(char, dict):
                        # 설명이 더 길면 업데이트 (정보 보강)
                        new_desc = char.get('description', '')
                        if len(new_desc) > len(character_dict[char_name]['description']):
                            character_dict[char_name]['description'] = new_desc
                        
                        # Traits 통합 (중복 제거)
                        new_traits = char.get('traits', [])
                        if new_traits:
                            existing_traits = character_dict[char_name]['traits']
                            for t in new_traits:
                                if t not in existing_traits:
                                    existing_traits.append(t)
            
            # 장소 정보 추출 및 집계
            for loc in metadata.get('locations', []):
                loc_name = AnalysisService._entity_name(loc)
                if loc_name and loc_name not in location_dict:
                    location_dict[loc_name] = {
                        'name': loc_name,
                        'description': loc.get('description', '') if isinstance(loc, dict) else '',
                        'scenes': [scene.chunk_index]
                    }
                elif loc_name:
                    # 기존 장소의 추가 등장 기록
                    if scene.chunk_index not in location_dict[loc_name]['scenes']:
                        location_dict[loc_name]['scenes'].append(scene.chunk_index)

            # 아이템 정보 추출 및 집계
            for item in metadata.get('items', []):
                item_name = AnalysisService._entity_name(item)
                if item_name and item_name not in item_dict:
                    item_dict[item_name] = {
                        'name': item_name,
                        'description': item.get('description', '') if isinstance(item, dict) else '',
                        'first_appearance': scene.chunk_index,
                        'significance': item.get('significance', '') if isinstance(item, dict) else ''
                    }

            # 주요 사건 추출
            if 'key_events' in metadata:
                for event in metadata['key_events']:
                    event_summary = AnalysisService._entity_name(event, 'summary')
                    bible_data["key_events"].append({
                        "summary": event_summary,
                        "scene_index": scene.chunk_index,
                        "characters_involved": metadata.get('characters', [])
                    })

        # 딕셔너리를 리스트로 변환
        bible_data["characters"] = list(character_dict.values())
        bible_data["locations"] = list(location_dict.values())
        bible_data["items"] = list(item_dict.values())

        return bible_data

    @staticmethod
    def get_bible_summary(
        db: Session,
        novel_id: int,
        chapter_id: int = None,
        max_chars: int = 2000
    ) -> str:
        """
        Analysis DB에서 압축된 바이블 요약 텍스트 반환.
        LLM 프롬프트에 직접 주입하기 위한 간결한 텍스트 형식.
        분석 데이터가 없으면 빈 문자열 반환.
        TTL 캐시 적용 (5분).
        """
        # TTL 캐시 확인
        cache_key = (novel_id, chapter_id)
        now = time.time()
        with _bible_summary_lock:
            cached = _bible_summary_cache.get(cache_key)
            if cached and (now - cached[1]) < _BIBLE_SUMMARY_TTL:
                return cached[0]

        query = db.query(Analysis).filter(
            Analysis.novel_id == novel_id,
            Analysis.analysis_type == AnalysisType.CHARACTER
        )
        if chapter_id:
            query = query.filter(Analysis.chapter_id == chapter_id)
        analysis = query.order_by(Analysis.updated_at.desc()).first()

        if not analysis or not analysis.result:
            with _bible_summary_lock:
                _bible_summary_cache[cache_key] = ("", now)
            return ""

        result = analysis.result
        parts = []

        characters = result.get('characters', [])[:8]
        if characters:
            lines = []
            for c in characters:
                traits = ", ".join(c.get('traits', [])[:3])
                desc = c.get('description', '')[:80]
                lines.append(f"- {c.get('name','')}: {desc} [{traits}]")
            parts.append("[등장인물]\n" + "\n".join(lines))

        relationships = result.get('relationships', [])[:8]
        if relationships:
            lines = [
                f"- {r.get('character1','')}-{r.get('character2','')}: {r.get('relation', '')} - {r.get('description','')[:60]}"
                for r in relationships
            ]
            parts.append("[관계]\n" + "\n".join(lines))

        key_events = result.get('key_events', [])[:5]
        if key_events:
            lines = []
            for e in key_events:
                importance = e.get('importance', '')
                prefix = "★ " if importance == "상" else "- "
                lines.append(f"{prefix}{e.get('summary', '')[:80]}")
            parts.append("[핵심사건]\n" + "\n".join(lines))

        locations = result.get('locations', [])[:3]
        if locations:
            lines = [f"- {loc.get('name','')}: {loc.get('description','')[:50]}" for loc in locations]
            parts.append("[주요장소]\n" + "\n".join(lines))

        summary = "\n\n".join(parts)[:max_chars]
        # 캐시 크기 제한: 초과 시 만료 항목 먼저 제거, 여전히 초과 시 가장 오래된 절반 제거
        with _bible_summary_lock:
            if len(_bible_summary_cache) > _BIBLE_SUMMARY_MAX_SIZE:
                expired = [k for k, v in _bible_summary_cache.items() if (now - v[1]) >= _BIBLE_SUMMARY_TTL]
                for k in expired:
                    del _bible_summary_cache[k]
                if len(_bible_summary_cache) > _BIBLE_SUMMARY_MAX_SIZE:
                    sorted_keys = sorted(_bible_summary_cache.keys(), key=lambda k: _bible_summary_cache[k][1])
                    for k in sorted_keys[:len(_bible_summary_cache) // 2]:
                        del _bible_summary_cache[k]
            _bible_summary_cache[cache_key] = (summary, now)
        return summary
