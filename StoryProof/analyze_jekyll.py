"""
지킬 파일의 구조 상세 분석
"""
import re
import sys
sys.path.append('.')

from story_analyzer import DocumentLoader, SceneChunker

def analyze_jekyll_structure():
    loader = DocumentLoader()
    jekyll_text = loader.load_txt('novel_corpus_kr/KR_horror_jekyll.txt')
    
    # 문장 분할
    sentences = re.split(r'([.!?]\s+)', jekyll_text)
    merged_sentences = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            merged_sentences.append(sentences[i] + sentences[i + 1])
        else:
            merged_sentences.append(sentences[i])
    
    merged_sentences = [s.strip() for s in merged_sentences if s.strip()]
    
    print("=" * 80)
    print("🔍 지킬 파일 구조 상세 분석")
    print("=" * 80)
    print(f"총 문장 수: {len(merged_sentences)}")
    print(f"전체 길이: {len(jekyll_text):,} 글자")
    print(f"평균 문장 길이: {len(jekyll_text) / len(merged_sentences):.0f} 글자")
    
    # 점수 요소 분석
    location_count = 0
    time_transition_count = 0
    separator_count = 0
    dialogue_count = 0
    
    chunker = SceneChunker()
    
    for sent in merged_sentences[:100]:  # 처음 100문장 분석
        if chunker.contains_new_location(sent):
            location_count += 1
        if any(word in sent for word in chunker.TIME_TRANSITIONS):
            time_transition_count += 1
        if "***" in sent or "---" in sent:
            separator_count += 1
        if sent.strip().startswith('"') or sent.strip().startswith("'"):
            dialogue_count += 1
    
    print(f"\n처음 100문장의 점수 요소 분석:")
    print(f"  - 위치 변화 감지: {location_count}개")
    print(f"  - 시간 전환: {time_transition_count}개")
    print(f"  - 구분자 (***,---): {separator_count}개")
    print(f"  - 대화: {dialogue_count}개")
    
    # 청크별 점수 분포 확인
    print("\n" + "=" * 80)
    print("📊 청크별 분할 점수 분석")
    print("=" * 80)
    
    scores = []
    current_score = 0
    
    for i, sent in enumerate(merged_sentences):
        if "***" in sent or "---" in sent:
            current_score += 12
        if "\n\n" in sent or sent.count('\n') >= 2:
            current_score += 5
        if chunker.contains_new_location(sent):
            current_score += 4
        if any(word in sent for word in chunker.TIME_TRANSITIONS):
            current_score += 3
        is_dialogue = sent.strip().startswith('"') or sent.strip().startswith("'")
        if is_dialogue and i > 0:
            prev_dialogue = merged_sentences[i-1].strip().startswith('"') or merged_sentences[i-1].strip().startswith("'")
            if is_dialogue != prev_dialogue:
                current_score += 2
        
        current_score += 1  # 문장마다 1점
        scores.append(current_score)
        
        # 임계값 20 기준으로 분할되는 위치 확인
        if current_score >= 20 and i < 50:
            print(f"분할점 #{i}: {current_score}점 - {sent[:60]}...")
            current_score = 0
    
    print(f"\n평균 분할 점수: {sum(scores) / len(scores):.1f}")

if __name__ == "__main__":
    analyze_jekyll_structure()
