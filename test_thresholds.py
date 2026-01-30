"""
청킹 성능 비교 - 다양한 임계값 테스트
"""
import re
import sys
from typing import List

sys.path.append('.')

from story_analyzer import SceneChunker, DocumentLoader

def test_threshold_values():
    """다양한 임계값으로 테스트"""
    loader = DocumentLoader()
    
    # 앨리스와 지킬 로드
    alice_text = loader.load_txt('novel_corpus_kr/KR_fantasy_alice.txt')
    jekyll_text = loader.load_txt('novel_corpus_kr/KR_horror_jekyll.txt')
    
    print("=" * 80)
    print("🧪 다양한 임계값 테스트 (동적 임계값 비활성화)")
    print("=" * 80)
    
    # 앨리스와 지킬을 동일한 임계값으로 테스트
    for threshold in [8, 12, 15, 20]:
        print(f"\n--- 임계값 = {threshold} ---")
        
        chunker = SceneChunker(threshold=threshold)
        
        # 동적 계산을 우회하기 위해 직접 설정
        chunker.mode = "scene"
        chunker.current_threshold = threshold
        
        # 수동으로 분할
        alice_scenes = chunker.split_into_scenes(alice_text)
        jekyll_scenes = chunker.split_into_scenes(jekyll_text)
        
        alice_avg = sum(len(s) for s in alice_scenes) / len(alice_scenes)
        jekyll_avg = sum(len(s) for s in jekyll_scenes) / len(jekyll_scenes)
        
        print(f"앨리스: {len(alice_scenes):3d}개 청크, 평균 {alice_avg:6.0f}글자")
        print(f"지킬:   {len(jekyll_scenes):3d}개 청크, 평균 {jekyll_avg:6.0f}글자")
        print(f"비율:   {len(jekyll_scenes)/len(alice_scenes):.2f}:1")

if __name__ == "__main__":
    test_threshold_values()
