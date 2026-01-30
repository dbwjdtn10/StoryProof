"""
청킹 균형 분석 - 최적 임계값 찾기
"""
import re
import sys
from typing import List

sys.path.append('.')

from story_analyzer import DocumentLoader

def manual_chunk_test(text, threshold):
    """임계값으로 수동 청킹"""
    sentences = re.split(r'([.!?]\s+)', text)
    merged_sentences = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            merged_sentences.append(sentences[i] + sentences[i + 1])
        else:
            merged_sentences.append(sentences[i])
    
    merged_sentences = [s.strip() for s in merged_sentences if s.strip()]
    
    scenes = []
    current_scene = []
    score = 0
    sentence_count = 0
    
    for sent in merged_sentences:
        current_scene.append(sent)
        sentence_count += 1
        
        # 점수 누적 (간단한 버전)
        if "***" in sent or "---" in sent:
            score += 12
        elif "\n\n" in sent:
            score += 5
        else:
            score += 1  # 평균적으로 문장 하나당 약 1점
        
        if score >= threshold and sentence_count >= 3:
            scenes.append(" ".join(current_scene))
            current_scene = []
            score = 0
            sentence_count = 0
    
    if current_scene:
        scenes.append(" ".join(current_scene))
    
    return scenes

def analyze():
    loader = DocumentLoader()
    
    alice_text = loader.load_txt('novel_corpus_kr/KR_fantasy_alice.txt')
    jekyll_text = loader.load_txt('novel_corpus_kr/KR_horror_jekyll.txt')
    
    print("=" * 80)
    print("📊 임계값별 청킹 결과 비교")
    print("=" * 80)
    print(f"파일 크기: 앨리스 {len(alice_text):,}글자, 지킬 {len(jekyll_text):,}글자 (비율: {len(jekyll_text)/len(alice_text):.2f}:1)\n")
    
    for threshold in [10, 15, 20, 25]:
        alice_chunks = manual_chunk_test(alice_text, threshold)
        jekyll_chunks = manual_chunk_test(jekyll_text, threshold)
        
        alice_avg = sum(len(c) for c in alice_chunks) / len(alice_chunks)
        jekyll_avg = sum(len(c) for c in jekyll_chunks) / len(jekyll_chunks)
        ratio = len(jekyll_chunks) / len(alice_chunks)
        
        print(f"임계값 {threshold:2d}:")
        print(f"  앨리스: {len(alice_chunks):3d}개 (평균 {alice_avg:5.0f}글자)")
        print(f"  지킬:   {len(jekyll_chunks):3d}개 (평균 {jekyll_avg:5.0f}글자)")
        print(f"  청킹 비율: {ratio:.2f}:1")
        print()

if __name__ == "__main__":
    analyze()
