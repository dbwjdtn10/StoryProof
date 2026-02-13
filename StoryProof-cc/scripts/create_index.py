import os
import sys
import time
from pinecone import Pinecone, ServerlessSpec

# 프로젝트 루트 경로 추가 (backend 모듈 import를 위해)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import settings

def create_pinecone_index():
    # ==========================================
    # 1. 설정 (API 키와 환경 설정)
    # ==========================================
    api_key = settings.PINECONE_API_KEY
    if not api_key:
        print("❌ Error: PINECONE_API_KEY is not set in .env file.")
        return

    # 생성할 인덱스 이름 (설정에서 가져오거나 기본값 사용)
    index_name = "story-child-index-384"
    
    # ==========================================
    # 2. Pinecone 클라이언트 초기화
    # ==========================================
    try:
        pc = Pinecone(api_key=api_key)
    except Exception as e:
        print(f"❌ Pinecone Client Initialization Failed: {e}")
        return

    # ==========================================
    # 3. 인덱스 생성
    # ==========================================
    print(f"Checking existing indexes...")
    existing_indexes = [index_info['name'] for index_info in pc.list_indexes()]

    if index_name not in existing_indexes:
        print(f"Creating index '{index_name}'...")
        
        try:
            pc.create_index(
                name=index_name,
                dimension=384,  # [중요] e5-small 모델 차원 수
                metric="cosine", # 문장 유사도 검색
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1" # Free Tier Default
                )
            )
            print("Index creating... waiting for readiness.")
            
            # 인덱스가 준비될 때까지 대기
            while not pc.describe_index(index_name).status['ready']:
                time.sleep(1)
                
            print(f"Index '{index_name}' successfully created!")
            
        except Exception as e:
            print(f"Creation Failed: {e}")
    else:
        print(f"Index '{index_name}' already exists.")

    # ==========================================
    # 4. 인덱스 정보 확인
    # ==========================================
    try:
        index_info = pc.describe_index(index_name)
        print(f"\n[Index Info]")
        print(f"Name: {index_info.name}")
        print(f"Dimension: {index_info.dimension}")
        print(f"Status: {index_info.status['state']}")
    except Exception as e:
        print(f"Could not retrieve index info: {e}")

if __name__ == "__main__":
    create_pinecone_index()
