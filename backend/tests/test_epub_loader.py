"""EPUB 로더 단위 테스트

메모리에서 최소 구조의 EPUB을 생성하여 파싱을 검증한다 (파일 픽스처 불필요).
실행: pytest backend/tests/test_epub_loader.py -v
"""

import io
import zipfile

import pytest

from backend.services.analysis.epub_loader import (
    extract_epub_chapters, extract_epub_text,
)


CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

CONTENT_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>테스트 소설</dc:title>
  </metadata>
  <manifest>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
    <item id="css" href="style.css" media-type="text/css"/>
  </manifest>
  <spine>
    <itemref idref="ch1"/>
    <itemref idref="ch2"/>
  </spine>
</package>"""


def _make_chapter_xhtml(title: str, paragraphs: list) -> str:
    body = "".join(f"<p>{p}</p>" for p in paragraphs)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title><style>p {{ color: red; }}</style></head>
<body><h1>{title}</h1>{body}</body>
</html>"""


def _build_epub() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml", CONTAINER_XML)
        zf.writestr("OEBPS/content.opf", CONTENT_OPF)
        zf.writestr("OEBPS/ch1.xhtml", _make_chapter_xhtml(
            "1화. 시작", ["주인공 위드는 조각사가 되었다.", "달빛이 비쳤다."]))
        zf.writestr("OEBPS/ch2.xhtml", _make_chapter_xhtml(
            "2화. 각성", ["위드는 사냥을 시작했다."]))
        zf.writestr("OEBPS/style.css", "p { color: red; }")
    return buf.getvalue()


def test_extract_chapters_follows_spine_order():
    chapters = extract_epub_chapters(_build_epub())
    assert len(chapters) == 2
    assert chapters[0][0] == "1화. 시작"
    assert chapters[1][0] == "2화. 각성"
    assert "주인공 위드는 조각사가 되었다." in chapters[0][1]
    assert "위드는 사냥을 시작했다." in chapters[1][1]


def test_html_tags_and_styles_stripped():
    chapters = extract_epub_chapters(_build_epub())
    for _, text in chapters:
        assert "<p>" not in text
        assert "color: red" not in text  # <style> 내용 제거


def test_extract_text_merges_all_chapters():
    text = extract_epub_text(_build_epub())
    assert "달빛이 비쳤다." in text
    assert "위드는 사냥을 시작했다." in text


def test_invalid_zip_raises_value_error():
    with pytest.raises(ValueError):
        extract_epub_chapters(b"this is not a zip file")


def test_zip_without_container_raises_value_error():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("hello.txt", "not an epub")
    with pytest.raises(ValueError):
        extract_epub_chapters(buf.getvalue())
