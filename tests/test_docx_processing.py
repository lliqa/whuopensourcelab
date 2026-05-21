from __future__ import annotations

import zipfile
import unittest
from io import BytesIO
from xml.etree import ElementTree as ET

from docx_style_tree import analyze_docx, replace_styles
from docx_style_tree.ooxml import NS, attr


class DocxProcessingTest(unittest.TestCase):
    def test_analyze_docx_builds_heading_tree(self) -> None:
        docx = _make_docx()

        result = analyze_docx(docx)

        tree = result["tree"]
        self.assertEqual(result["node_count"], 3)
        self.assertEqual(tree["children"][0]["title"], "Chapter One")
        self.assertEqual(tree["children"][0]["children"][0]["title"], "Section One")
        self.assertEqual(tree["children"][0]["children"][0]["content"][0]["text"], "Body text")

    def test_replace_styles_updates_structural_paragraph_styles(self) -> None:
        docx = _make_docx()

        output = replace_styles(docx, {"heading_1": "Custom Heading 1", "heading_2": "Custom Heading 2"})

        with zipfile.ZipFile(BytesIO(output)) as package:
            root = ET.fromstring(package.read("word/document.xml"))

        styles = [
            attr(style, "val")
            for style in root.findall(".//w:pPr/w:pStyle", NS)
        ]
        self.assertEqual(styles[:2], ["CustomHeading1", "CustomHeading2"])

    def test_analyze_docx_detects_chinese_plain_text_headings(self) -> None:
        docx = _make_docx(
            paragraphs=[
                (None, "第一、注册华为ICT人才账号"),
                (None, "登录，并打开网址"),
                (None, "习题解析"),
                (None, "单选题、"),
                (None, "1、这是一道题，不应作为章节标题"),
            ]
        )

        result = analyze_docx(docx)

        root = result["tree"]
        self.assertEqual(result["node_count"], 4)
        self.assertEqual(root["children"][0]["title"], "第一、注册华为ICT人才账号")
        self.assertEqual(root["children"][0]["children"][0]["title"], "习题解析")
        self.assertEqual(root["children"][0]["children"][0]["children"][0]["title"], "单选题、")
        question_content = root["children"][0]["children"][0]["children"][0]["content"][0]["text"]
        self.assertEqual(question_content, "1、这是一道题，不应作为章节标题")


def _make_docx(paragraphs: list[tuple[str | None, str]] | None = None) -> bytes:
    if paragraphs is None:
        paragraphs = [
            ("Heading1", "Chapter One"),
            ("Heading2", "Section One"),
            ("Normal", "Body text"),
        ]

    body = "\n".join(_paragraph_xml(style_id, text) for style_id, text in paragraphs)
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
  </w:body>
</w:document>
"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="Heading 1"/></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="Heading 2"/></w:style>
  <w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="CustomHeading1"><w:name w:val="Custom Heading 1"/></w:style>
  <w:style w:type="paragraph" w:styleId="CustomHeading2"><w:name w:val="Custom Heading 2"/></w:style>
</w:styles>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
</Types>
"""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", content_types)
        package.writestr("word/document.xml", document_xml)
        package.writestr("word/styles.xml", styles_xml)
    return buffer.getvalue()


def _paragraph_xml(style_id: str | None, text: str) -> str:
    style_xml = f'<w:pPr><w:pStyle w:val="{style_id}"/></w:pPr>' if style_id else ""
    return f"<w:p>{style_xml}<w:r><w:t>{text}</w:t></w:r></w:p>"


if __name__ == "__main__":
    unittest.main()
