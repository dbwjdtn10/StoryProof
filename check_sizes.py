"""
최종 청킹 크기 검증
"""
import sys
sys.path.append('.')

from story_analyzer import SceneChunker, DocumentLoader
import statistics

loader = DocumentLoader()
alice_text = loader.load_txt('novel_corpus_kr/KR_fantasy_alice.txt')
jekyll_text = loader.load_txt('novel_corpus_kr/KR_horror_jekyll.txt')

chunker = SceneChunker()
alice_chunks = chunker.split_into_scenes(alice_text)
jekyll_chunks = chunker.split_into_scenes(jekyll_text)

alice_lengths = [len(c) for c in alice_chunks]
jekyll_lengths = [len(c) for c in jekyll_chunks]

print("\n" + "=" * 60)
print("📊 최종 청킹 크기")
print("=" * 60)
print(f"\n앨리스:")
print(f"  청크 개수: {len(alice_chunks)}")
print(f"  청크당 평균: {statistics.mean(alice_lengths):.0f} 글자")
print(f"  중앙값: {statistics.median(alice_lengths):.0f} 글자")

print(f"\n지킬:")
print(f"  청크 개수: {len(jekyll_chunks)}")
print(f"  청크당 평균: {statistics.mean(jekyll_lengths):.0f} 글자")
print(f"  중앙값: {statistics.median(jekyll_lengths):.0f} 글자")

alice_avg = statistics.mean(alice_lengths)
jekyll_avg = statistics.mean(jekyll_lengths)

print(f"\n목표 3,000글자 대비:")
print(f"  앨리스: {alice_avg/3000*100:.1f}% (목표: 100%)")
print(f"  지킬:   {jekyll_avg/3000*100:.1f}% (목표: 100%)")
print("=" * 60 + "\n")
