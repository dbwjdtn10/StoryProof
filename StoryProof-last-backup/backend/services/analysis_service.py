from typing import Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.db.models import Novel, Chapter, Analysis, AnalysisType, VectorDocument

class AnalysisService:
    @staticmethod
    def get_chapter_bible(db: Session, novel_id: int, chapter_id: int, user_id: int, is_admin: bool = False) -> Dict[str, Any]:
        """
        회차의 스토리보드 바이블(인물, 아이템, 장소, 타임라인 등) 조회
        """
        # 1. 소설 및 권한 확인
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise HTTPException(status_code=404, detail="소설을 찾을 수 없습니다.")
        
        if novel.author_id != user_id and not is_admin and not novel.is_public:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")
        
        # 2. 회차 확인
        chapter = db.query(Chapter).filter(
            Chapter.id == chapter_id,
            Chapter.novel_id == novel_id
        ).first()
        
        if not chapter:
            raise HTTPException(status_code=404, detail="회차를 찾을 수 없습니다.")
        
        # 3. 분석 데이터 조회
        analysis_record = db.query(Analysis).filter(
            Analysis.chapter_id == chapter_id,
            Analysis.analysis_type == AnalysisType.CHARACTER
        ).first()
        
        # 3-1. 분석된 결과가 있으면 사용
        if analysis_record and analysis_record.result:
            result = analysis_record.result
            
            # 통계(appearance_count) 보강을 위해 VectorDocument 조회 (해당 회차로 한정)
            scenes = db.query(VectorDocument).filter(
                VectorDocument.novel_id == novel_id,
                VectorDocument.chapter_id == chapter_id
            ).order_by(VectorDocument.chunk_index).all()
            
            character_stats = {}
            for scene in scenes:
                metadata = scene.metadata_json or {}
                for char in metadata.get('characters', []):
                    # 문자열/딕셔너리 호환성 처리
                    if isinstance(char, dict):
                        char_name = char.get('name')
                    else:
                        char_name = char
                        
                    if char_name:
                        if char_name not in character_stats:
                            character_stats[char_name] = {'count': 0, 'appearances': []}
                        character_stats[char_name]['count'] += 1
                        character_stats[char_name]['appearances'].append(scene.chunk_index)
            
            # 분석 결과에 통계 보강
            if 'characters' in result:
                for char in result['characters']:
                    name = char.get('name')
                    if name and name in character_stats:
                        char['appearance_count'] = character_stats[name]['count']
                        char['appearances'] = character_stats[name]['appearances']
                    else:
                        if 'appearance_count' not in char:
                            char['appearance_count'] = 1
                        if 'appearances' not in char:
                            char['appearances'] = [char.get('first_appearance', 0)]
            
            # 씬 데이터 추가 (Partitioned rendering용)
            result['scenes'] = [
                {
                    'scene_index': s.chunk_index,
                    'original_text': s.chunk_text,
                    'summary': (s.metadata_json or {}).get('summary', '')
                } for s in scenes
            ]
            result['chapter_id'] = chapter_id
            
            return result

        # 3-2. 분석 결과가 없으면 VectorDocument 기반 집계 (레거시/실시간 집계)
        scenes = db.query(VectorDocument).filter(
            VectorDocument.novel_id == novel_id,
            VectorDocument.chapter_id == chapter_id
        ).order_by(VectorDocument.chunk_index).all()
        
        bible_data = {
            "characters": [],
            "locations": [],
            "items": [],
            "key_events": [],
            "timeline": [],
            "scenes": [],
            "chapter_id": chapter_id
        }
        
        # 씬 데이터 추가 (Partitioned rendering용)
        bible_data['scenes'] = [
            {
                'scene_index': s.chunk_index,
                'original_text': s.chunk_text,
                'summary': (s.metadata_json or {}).get('summary', '') or (s.chunk_text[:100] + "...")
            } for s in scenes
        ]
        
        character_dict = {}
        location_dict = {}
        item_dict = {}
        
        for scene in scenes:
            metadata = scene.metadata_json or {}
            
            # 인물 추출
            for char in metadata.get('characters', []):
                char_name = char.get('name') if isinstance(char, dict) else char
                if char_name and char_name not in character_dict:
                    character_dict[char_name] = {
                        'name': char_name,
                        'first_appearance': scene.chunk_index,
                        'appearances': [scene.chunk_index],
                        'description': char.get('description', '') if isinstance(char, dict) else '',
                        'traits': char.get('traits', []) if isinstance(char, dict) else []
                    }
                elif char_name:
                    if scene.chunk_index not in character_dict[char_name]['appearances']:
                        character_dict[char_name]['appearances'].append(scene.chunk_index)
            
            # 장소 추출
            for loc in metadata.get('locations', []):
                loc_name = loc.get('name') if isinstance(loc, dict) else loc
                if loc_name and loc_name not in location_dict:
                    location_dict[loc_name] = {
                        'name': loc_name,
                        'description': loc.get('description', '') if isinstance(loc, dict) else '',
                        'scenes': [scene.chunk_index]
                    }
                elif loc_name:
                    if scene.chunk_index not in location_dict[loc_name]['scenes']:
                        location_dict[loc_name]['scenes'].append(scene.chunk_index)

            # 아이템 추출
            for item in metadata.get('items', []):
                 item_name = item.get('name') if isinstance(item, dict) else item
                 if item_name and item_name not in item_dict:
                    item_dict[item_name] = {
                        'name': item_name,
                        'description': item.get('description', '') if isinstance(item, dict) else '',
                        'first_appearance': scene.chunk_index,
                        'significance': item.get('significance', '') if isinstance(item, dict) else ''
                    }

            # 주요 사건
            if 'key_events' in metadata:
                for event in metadata['key_events']:
                    event_summary = event.get('summary') if isinstance(event, dict) else event
                    bible_data["key_events"].append({
                        "summary": event_summary,
                        "scene_index": scene.chunk_index,
                        "characters_involved": metadata.get('characters', [])
                    })

        # List 변환
        bible_data["characters"] = list(character_dict.values())
        bible_data["locations"] = list(location_dict.values())
        bible_data["items"] = list(item_dict.values())
        
        return bible_data
