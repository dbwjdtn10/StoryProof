"""
최종 청킹 결과 검증
"""
import sys
sys.path.append('.')

from story_analyzer import SceneChunker, DocumentLoader
import statistics

def print_chunk_stats(name, chunks):
    """청크 통계 출력"""
    lengths = [len(c) for c in chunks]
    
    print(f"\n{name}:")
    print(f"  개수: {len(chunks)}")
    print(f"  총 길이: {sum(lengths):,} 글자")
    print(f"  평균: {statistics.mean(lengths):.0f} 글자")
    print(f"  중앙값: {statistics.median(lengths):.0f} 글자")
    print(f"  최소: {min(lengths)} 글자")
    print(f"  최대: {max(lengths)} 글자")
    print(f"  표준편차: {statistics.stdev(lengths):.0f} 글자")

def main():
    loader = DocumentLoader()
    
    print("=" * 80)
    print("📊 최종 청킹 결과 검증")
    print("=" * 80)
    
    alice_text = loader.load_txt('novel_corpus_kr/KR_fantasy_alice.txt')
    jekyll_text = loader.load_txt('novel_corpus_kr/KR_horror_jekyll.txt')
    
    chunker = SceneChunker(threshold=8)
    
    alice_chunks = chunker.split_into_scenes(alice_text)
    print_chunk_stats("앨리스 (명확한 챕터 구조)", alice_chunks)
    
    jekyll_chunks = chunker.split_into_scenes(jekyll_text)
    print_chunk_stats("지킬 (구조화되지 않음, 동적 임계값)", jekyll_chunks)
    
    print("\n" + "=" * 80)
    print("📈 비교 분석")
    print("=" * 80)
    
    file_ratio = len(jekyll_text) / len(alice_text)
    chunk_ratio = len(jekyll_chunks) / len(alice_chunks)
    
    print(f"파일 크기 비율: {file_ratio:.2f}:1")
    print(f"청킹 개수 비율: {chunk_ratio:.2f}:1")
    print(f"개선도: {524/len(jekyll_chunks):.1f}배 감소 (기존 524개 → {len(jekyll_chunks)}개)")
    
    # 세 번째 소설로도 테스트
    print("\n" + "=" * 80)
    print("🔍 다른 소설로 일관성 검증")
    print("=" * 80)
    
    for novel_file in ['KR_fantasy_oz.txt', 'KR_romance_gatsby.txt']:
        try:
            text = loader.load_txt(f'novel_corpus_kr/{novel_file}')
            chunks = chunker.split_into_scenes(text)
            lengths = [len(c) for c in chunks]
            print(f"\n{novel_file}:")
            print(f"  파일: {len(text):,} 글자, {len(chunks)} 청크, 청크당 {statistics.mean(lengths):.0f} 글자")
        except:
            pass

if __name__ == "__main__":
    main()
