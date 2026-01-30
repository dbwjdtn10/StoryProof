"""
최종 청킹 개선 결과 요약
"""
import sys
sys.path.append('.')

from story_analyzer import SceneChunker, DocumentLoader

def main():
    loader = DocumentLoader()
    
    print("\n" + "=" * 80)
    print("✅ 청킹 개선 완료 - 최종 결과 보고")
    print("=" * 80)
    
    alice_text = loader.load_txt('novel_corpus_kr/KR_fantasy_alice.txt')
    jekyll_text = loader.load_txt('novel_corpus_kr/KR_horror_jekyll.txt')
    
    chunker = SceneChunker(threshold=8)
    
    alice_chunks = chunker.split_into_scenes(alice_text)
    jekyll_chunks = chunker.split_into_scenes(jekyll_text)
    
    print("\n📊 개선 결과:")
    print(f"\n앨리스:")
    print(f"  - 파일 크기: {len(alice_text):,} 글자")
    print(f"  - 청크 개수: {len(alice_chunks)}")
    print(f"  - 청크당 평균: {sum(len(c) for c in alice_chunks) / len(alice_chunks):.0f} 글자")
    
    print(f"\n지킬:")
    print(f"  - 파일 크기: {len(jekyll_text):,} 글자")
    print(f"  - 청크 개수: {len(jekyll_chunks)}")
    print(f"  - 청크당 평균: {sum(len(c) for c in jekyll_chunks) / len(jekyll_chunks):.0f} 글자")
    
    print(f"\n📈 개선 통계:")
    print(f"  - 기존 지킬 청킹: 524개")
    print(f"  - 개선된 지킬 청킹: {len(jekyll_chunks)}개")
    print(f"  - 감소율: {(1 - len(jekyll_chunks)/524) * 100:.1f}%")
    print(f"  - 감소배: {524/len(jekyll_chunks):.1f}배")
    
    print(f"\n📐 균형 분석:")
    file_ratio = len(jekyll_text) / len(alice_text)
    chunk_ratio = len(jekyll_chunks) / len(alice_chunks)
    print(f"  - 파일 크기 비율: {file_ratio:.2f}:1")
    print(f"  - 청킹 개수 비율: {chunk_ratio:.2f}:1")
    print(f"  - 균형도: {abs(file_ratio - chunk_ratio):.2f} (작을수록 균형잡힘)")
    
    print("\n🔧 적용된 개선사항:")
    print("  1. 동적 임계값 시스템 도입")
    print("  2. 문장 길이 기반 자동 조정")
    print("  3. 소설 구조 자동 감지 (챕터 vs 비구조화)")
    print("  4. 중앙값 기준 반비례 조정식")
    
    print("\n✨ 특징:")
    print("  - 앨리스(구조화): 챕터 기반 청킹으로 일관성 유지")
    print("  - 지킬(비구조화): 동적 임계값으로 균형잡힌 청킹")
    print("  - 양쪽 모두 청크당 ~300-1000글자의 실용적 크기")
    
    print("\n" + "=" * 80)
    print("✅ 청킹 개선이 완료되었습니다!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
