"""
문서 로딩 모듈
=============
다양한 파일 형식(TXT, DOCX, PDF)에서 텍스트를 추출합니다.

주요 기능:
- 자동 인코딩 감지 (chardet 라이브러리 사용)
- 다중 인코딩 fallback 지원
- 한글 파일 처리 최적화 (cp949, euc-kr 지원)
"""


class DocumentLoader:
    """
    파일 로더 클래스
    
    다양한 인코딩으로 작성된 텍스트 파일을 안전하게 로드합니다.
    한국어 소설 파일의 경우 cp949, euc-kr 등 다양한 인코딩이 사용되므로
    자동 감지 및 fallback 메커니즘을 제공합니다.
    """
    
    @staticmethod
    def load_txt(file_path: str) -> str:
        """
        TXT 파일을 로드하고 텍스트를 반환합니다.
        
        동작 방식:
        1. chardet 라이브러리로 인코딩 자동 감지 시도
        2. 감지 신뢰도가 70% 이상이면 해당 인코딩 사용
        3. 실패 시 일반적인 인코딩 목록으로 순차 시도
        
        Args:
            file_path (str): 로드할 TXT 파일의 경로
            
        Returns:
            str: 파일의 텍스트 내용
            
        Raises:
            UnicodeDecodeError: 모든 인코딩 시도가 실패한 경우
            FileNotFoundError: 파일이 존재하지 않는 경우
            
        Example:
            >>> loader = DocumentLoader()
            >>> text = loader.load_txt("novel.txt")
            >>> print(f"로드된 텍스트 길이: {len(text)}")
        """
        # Step 1: chardet을 사용한 자동 인코딩 감지
        try:
            import chardet
            
            # 파일을 바이너리 모드로 읽어 인코딩 감지
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                detected_encoding = result['encoding']
                confidence = result['confidence']
                
                # 신뢰도가 70% 이상이면 감지된 인코딩 사용
                if confidence > 0.7 and detected_encoding:
                    try:
                        text = raw_data.decode(detected_encoding)
                        print(f"[OK] 파일 로드: {detected_encoding} (신뢰도: {confidence:.2f})")
                        return text
                    except Exception:
                        # 디코딩 실패 시 fallback으로 진행
                        pass
        except ImportError:
            # chardet이 설치되지 않은 경우 fallback으로 진행
            pass
        
        # Step 2: 일반적인 인코딩 목록으로 순차 시도
        # 한국어 파일에서 자주 사용되는 인코딩 우선 배치
        encodings = [
            'utf-8',      # 표준 유니코드 인코딩
            'cp949',      # Windows 한글 인코딩
            'euc-kr',     # Unix/Linux 한글 인코딩
            'utf-16',     # 일부 워드프로세서에서 사용
            'latin-1'     # 서유럽 언어 (마지막 fallback)
        ]
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='strict') as f:
                    text = f.read()
                    print(f"[OK] 파일 로드: {encoding}")
                    return text
            except (UnicodeDecodeError, UnicodeError, LookupError):
                # 현재 인코딩으로 디코딩 실패, 다음 인코딩 시도
                continue
        
        # Step 3: 모든 시도 실패 시 에러 발생
        raise UnicodeDecodeError(
            'unknown', b'', 0, 1,
            f"지원하지 않는 인코딩입니다. 시도한 인코딩: {encodings}"
        )
