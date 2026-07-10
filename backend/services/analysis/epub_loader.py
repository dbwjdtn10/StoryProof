"""
EPUB 로더
=========
전자책 표준 포맷(EPUB)에서 텍스트를 추출한다. 외부 의존성 없이
표준 라이브러리(zipfile + xml.etree + html.parser)만 사용.

- EPUB = ZIP 컨테이너: META-INF/container.xml → OPF(manifest/spine) → XHTML 문서들
- spine 순서대로 문서를 읽어 (제목, 본문) 목록으로 반환 → 회차 단위 임포트 지원
"""

import io
import logging
import posixpath
import zipfile
from html.parser import HTMLParser
from typing import List, Optional, Tuple
from urllib.parse import unquote
from xml.etree import ElementTree

logger = logging.getLogger(__name__)

_CONTAINER_NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
_OPF_NS = {"opf": "http://www.idpf.org/2007/opf"}

# 블록 레벨 태그 → 줄바꿈으로 변환
_BLOCK_TAGS = {
    "p", "div", "br", "li", "tr", "section", "article",
    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "hr",
}
_SKIP_TAGS = {"script", "style", "head"}
_TITLE_TAGS = {"h1", "h2", "h3", "title"}


class _EpubHTMLExtractor(HTMLParser):
    """XHTML에서 본문 텍스트와 제목 후보를 추출"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts: List[str] = []
        self._skip_depth = 0
        self._title_tag: Optional[str] = None
        self._title_parts: List[str] = []
        self.title: Optional[str] = None

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")
        if self.title is None and tag in _TITLE_TAGS and self._title_tag is None:
            self._title_tag = tag
            self._title_parts = []

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")
        if tag == self._title_tag:
            candidate = "".join(self._title_parts).strip()
            if candidate:
                self.title = candidate
            self._title_tag = None

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        self._parts.append(data)
        if self._title_tag is not None:
            self._title_parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        # 연속 공백/빈 줄 정리
        lines = [" ".join(line.split()) for line in raw.splitlines()]
        cleaned = [line for line in lines if line]
        return "\n".join(cleaned)


def _html_to_text(html_bytes: bytes) -> Tuple[str, Optional[str]]:
    """XHTML 바이트 → (본문 텍스트, 제목 후보)"""
    for encoding in ("utf-8", "utf-16", "cp949", "latin-1"):
        try:
            html = html_bytes.decode(encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        return "", None

    extractor = _EpubHTMLExtractor()
    try:
        extractor.feed(html)
    except Exception as e:
        logger.warning(f"[EPUB] HTML 파싱 실패 (무시): {e}")
    return extractor.get_text(), extractor.title


def extract_epub_chapters(raw_data: bytes) -> List[Tuple[str, str]]:
    """EPUB 바이트에서 spine 순서대로 (제목, 본문) 목록 추출

    Raises:
        ValueError: 유효한 EPUB이 아니거나 텍스트를 추출할 수 없는 경우
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw_data))
    except zipfile.BadZipFile:
        raise ValueError("유효한 EPUB 파일이 아닙니다 (ZIP 컨테이너 아님).")

    try:
        container = ElementTree.fromstring(zf.read("META-INF/container.xml"))
        rootfile = container.find(".//c:rootfile", _CONTAINER_NS)
        opf_path = rootfile.get("full-path")
        opf = ElementTree.fromstring(zf.read(opf_path))
    except Exception as e:
        raise ValueError(f"EPUB 메타데이터(OPF)를 읽을 수 없습니다: {e}")

    manifest = {
        item.get("id"): item.get("href")
        for item in opf.findall(".//opf:manifest/opf:item", _OPF_NS)
    }
    spine_ids = [
        ref.get("idref")
        for ref in opf.findall(".//opf:spine/opf:itemref", _OPF_NS)
    ]
    base_dir = posixpath.dirname(opf_path)

    chapters: List[Tuple[str, str]] = []
    for idref in spine_ids:
        href = manifest.get(idref)
        if not href:
            continue
        path = posixpath.normpath(posixpath.join(base_dir, unquote(href)) if base_dir else unquote(href))
        try:
            html_bytes = zf.read(path)
        except KeyError:
            logger.warning(f"[EPUB] spine 문서를 찾을 수 없음: {path}")
            continue

        text, title = _html_to_text(html_bytes)
        if text.strip():
            chapters.append((title or f"{len(chapters) + 1}장", text))

    if not chapters:
        raise ValueError("EPUB에서 텍스트를 추출할 수 없습니다.")
    return chapters


def extract_epub_text(raw_data: bytes) -> str:
    """EPUB 전체를 하나의 텍스트로 병합 (단일 회차 업로드용)"""
    chapters = extract_epub_chapters(raw_data)
    return "\n\n".join(text for _, text in chapters)
