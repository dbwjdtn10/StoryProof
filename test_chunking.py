"""
청킹 성능 분석 및 개선 테스트
"""
import re
import sys
from typing import List

sys.path.append('.')

from story_analyzer import SceneChunker, DocumentLoader

def analyze_chunking():
    """두 소설의 청킹 결과 분석"""
    loader = DocumentLoader()
    
    # 앨리스와 지킬 로드
    alice_text = loader.load_txt('novel_corpus_kr/KR_fantasy_alice.txt')
    jekyll_text = loader.load_txt('novel_corpus_kr/KR_horror_jekyll.txt')
    
    print("=" * 80)
    print("📊 기존 청킹 결과")
    print("=" * 80)
    
    chunker = SceneChunker(threshold=8)
    
    alice_scenes = chunker.split_into_scenes(alice_text)
    print(f"앨리스 (원본): {len(alice_scenes)}개 청크")
    print(f"  - 평균 길이: {sum(len(s) for s in alice_scenes) / len(alice_scenes):.0f} 글자")
    print(f"  - 최대 길이: {max(len(s) for s in alice_scenes):.0f} 글자")
    print(f"  - 최소 길이: {min(len(s) for s in alice_scenes):.0f} 글자")
    
    jekyll_scenes = chunker.split_into_scenes(jekyll_text)
    print(f"\n지킬 (원본): {len(jekyll_scenes)}개 청크")
    print(f"  - 평균 길이: {sum(len(s) for s in jekyll_scenes) / len(jekyll_scenes):.0f} 글자")
    print(f"  - 최대 길이: {max(len(s) for s in jekyll_scenes):.0f} 글자")
    print(f"  - 최소 길이: {min(len(s) for s in jekyll_scenes):.0f} 글자")
    
    print(f"\n파일 크기: 앨리스 {len(alice_text):,} 글자, 지킬 {len(jekyll_text):,} 글자")
    print(f"크기 비율: 지킬/앨리스 = {len(jekyll_text)/len(alice_text):.2f}")
    print(f"청킹 비율: 지킬/앨리스 = {len(jekyll_scenes)/len(alice_scenes):.2f}")
    
    # 세부 분석
    print("\n" + "=" * 80)
    print("🔍 지킬이 과도하게 청킹되는 이유 분석")
    print("=" * 80)
    
    # 문장 수 비교
    alice_sents = re.split(r'([.!?]\s+)', alice_text)
    jekyll_sents = re.split(r'([.!?]\s+)', jekyll_text)
    
    print(f"앨리스 문장 수: {len(alice_sents) // 2:.0f}개")
    print(f"지킬 문장 수: {len(jekyll_sents) // 2:.0f}개")
    
    # 청크당 문장 수
    def count_sentences_in_chunk(chunk):
        return len(re.split(r'[.!?]+', chunk)) - 1
    
    alice_avg_sents = sum(count_sentences_in_chunk(s) for s in alice_scenes) / len(alice_scenes)
    jekyll_avg_sents = sum(count_sentences_in_chunk(s) for s in jekyll_scenes) / len(jekyll_scenes)
    
    print(f"\n청크당 평균 문장 수:")
    print(f"  - 앨리스: {alice_avg_sents:.1f}개")
    print(f"  - 지킬: {jekyll_avg_sents:.1f}개")
    
    # 지킬의 첫 10개 청크 샘플 확인
    print("\n" + "=" * 80)
    print("🔎 지킬의 첫 5개 청크 샘플 (길이 확인)")
    print("=" * 80)
    for i, chunk in enumerate(jekyll_scenes[:5]):
        sents = count_sentences_in_chunk(chunk)
        print(f"청크 {i+1}: {len(chunk):4d}글자, {sents:2d}문장 - {chunk[:80]}...")

if __name__ == "__main__":
    analyze_chunking()
