"""
공통 유틸리티 함수
"""


def sanitize_filename(text: str, max_length: int = 30) -> str:
    """
    파일명에 사용할 수 없는 문자를 제거하고 길이를 제한합니다.

    Args:
        text: 원본 텍스트
        max_length: 최대 길이 (기본 30자)

    Returns:
        str: 안전한 파일명 문자열
    """
    safe = "".join(c for c in text if c.isalnum() or c in " _-").strip()
    return safe[:max_length] if safe else "untitled"
