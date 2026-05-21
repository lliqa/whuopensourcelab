from __future__ import annotations

import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from docx_style_tree import analyze_docx, replace_styles
from docx_style_tree.errors import InvalidDocxError, InvalidStyleMapError
from docx_style_tree.ooxml import NS, attr, paragraph_text
from docx_style_tree.style_replacer import load_style_map, normalize_style_map


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

        output = replace_styles(
            docx, {"heading_1": "Custom Heading 1", "heading_2": "Custom Heading 2"}
        )

        with zipfile.ZipFile(BytesIO(output)) as package:
            root = ET.fromstring(package.read("word/document.xml"))

        styles = [attr(style, "val") for style in root.findall(".//w:pPr/w:pStyle", NS)]
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

    def test_analyze_docx_allows_missing_styles_part(self) -> None:
        docx = _make_docx(include_styles=False)

        result = analyze_docx(docx)

        self.assertEqual(result["node_count"], 3)
        self.assertIsNone(result["tree"]["children"][0]["style_name"])

    def test_analyze_docx_reports_malformed_xml_as_invalid_docx(self) -> None:
        docx = _make_broken_docx()

        with self.assertRaises(InvalidDocxError):
            analyze_docx(docx)

    def test_analyze_docx_reports_bad_zip_as_invalid_docx(self) -> None:
        with self.assertRaises(InvalidDocxError):
            analyze_docx(b"not a zip")

    def test_analyze_docx_handles_document_without_body(self) -> None:
        docx = _make_docx_from_document_xml(
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
        )

        result = analyze_docx(docx)

        self.assertEqual(result["node_count"], 1)
        self.assertEqual(result["tree"]["children"], [])

    def test_analyze_docx_detects_outline_level_heading(self) -> None:
        docx = _make_docx(
            body_xml=(
                '<w:p><w:pPr><w:outlineLvl w:val="2"/></w:pPr>'
                "<w:r><w:t>Outline Heading</w:t></w:r></w:p>"
            )
        )

        result = analyze_docx(docx)

        self.assertEqual(result["tree"]["children"][0]["level"], 3)

    def test_extract_table_preserves_text_controls(self) -> None:
        docx = _make_docx(
            body_xml="\n".join(
                [
                    _paragraph_xml("Heading1", "Chapter One"),
                    "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>A</w:t><w:tab/>"
                    "<w:t>B</w:t><w:br/><w:t>C</w:t></w:r></w:p></w:tc></w:tr></w:tbl>",
                ]
            )
        )

        result = analyze_docx(docx)

        rows = result["tree"]["children"][0]["content"][0]["rows"]
        self.assertEqual(rows, [["A\tB\nC"]])

    def test_replace_styles_adds_missing_target_style(self) -> None:
        docx = _make_docx()

        output = replace_styles(docx, {"heading_1": "Missing Heading"})

        self.assertEqual(_paragraph_style_values(output)[0], "MissingHeading")
        with zipfile.ZipFile(BytesIO(output)) as package:
            styles_root = ET.fromstring(package.read("word/styles.xml"))
        created_style = styles_root.find('.//w:style[@w:styleId="MissingHeading"]', NS)
        self.assertIsNotNone(created_style)

    def test_replace_styles_reports_bad_zip_as_invalid_docx(self) -> None:
        with self.assertRaises(InvalidDocxError):
            replace_styles(b"not a zip")

    def test_replace_styles_with_empty_mapping_keeps_styles(self) -> None:
        output = replace_styles(_make_docx(), {})

        self.assertEqual(_paragraph_style_values(output)[:3], ["Heading1", "Heading2", "Normal"])

    def test_replace_styles_handles_document_without_body(self) -> None:
        docx = _make_docx_from_document_xml(
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
        )

        output = replace_styles(docx, {})

        with zipfile.ZipFile(BytesIO(output)) as package:
            self.assertIn("word/document.xml", package.namelist())

    def test_replace_styles_skips_non_structural_paragraphs(self) -> None:
        body_xml = "\n".join(
            [
                _paragraph_xml("Heading1", "Chapter One"),
                _paragraph_xml("Caption", "Figure 1"),
                _paragraph_xml("Normal", "Body text"),
                _paragraph_xml("Normal", "List text", list_item=True),
                _table_xml("Normal", "Table text"),
            ]
        )
        docx = _make_docx(body_xml=body_xml)

        output = replace_styles(docx, {"heading_1": "Custom Heading 1", "normal": "Custom Normal"})

        self.assertEqual(
            _paragraph_style_values(output),
            ["CustomHeading1", "Caption", "CustomNormal", "Normal", "Normal"],
        )

    def test_load_style_map_rejects_non_object_json(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "styles.json"
            path.write_text("[]", encoding="utf-8")

            with self.assertRaises(InvalidStyleMapError):
                load_style_map(path)

    def test_normalize_style_map_rejects_empty_value(self) -> None:
        with self.assertRaises(InvalidStyleMapError):
            normalize_style_map({"heading_1": ""})

    def test_paragraph_text_handles_tabs_and_breaks(self) -> None:
        paragraph = ET.fromstring(
            '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:r><w:t>A</w:t><w:tab/><w:t>B</w:t><w:cr/><w:t>C</w:t></w:r>"
            "</w:p>"
        )

        self.assertEqual(paragraph_text(paragraph), "A\tB\nC")


def _make_docx(
    paragraphs: list[tuple[str | None, str]] | None = None,
    *,
    body_xml: str | None = None,
    include_styles: bool = True,
) -> bytes:
    if paragraphs is None:
        paragraphs = [
            ("Heading1", "Chapter One"),
            ("Heading2", "Section One"),
            ("Normal", "Body text"),
        ]

    body = body_xml or "\n".join(_paragraph_xml(style_id, text) for style_id, text in paragraphs)
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
  </w:body>
</w:document>
"""
    styles_xml = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
            '  <w:style w:type="paragraph" w:styleId="Heading1">',
            '    <w:name w:val="Heading 1"/>',
            "  </w:style>",
            '  <w:style w:type="paragraph" w:styleId="Heading2">',
            '    <w:name w:val="Heading 2"/>',
            "  </w:style>",
            '  <w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>',
            '  <w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="Caption"/></w:style>',
            '  <w:style w:type="paragraph" w:styleId="CustomNormal">',
            '    <w:name w:val="Custom Normal"/>',
            "  </w:style>",
            '  <w:style w:type="paragraph" w:styleId="CustomHeading1">',
            '    <w:name w:val="Custom Heading 1"/>',
            "  </w:style>",
            '  <w:style w:type="paragraph" w:styleId="CustomHeading2">',
            '    <w:name w:val="Custom Heading 2"/>',
            "  </w:style>",
            "</w:styles>",
        ]
    )
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
</Types>
"""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", content_types)
        package.writestr("word/document.xml", document_xml)
        if include_styles:
            package.writestr("word/styles.xml", styles_xml)
    return buffer.getvalue()


def _paragraph_xml(style_id: str | None, text: str, *, list_item: bool = False) -> str:
    ppr_parts: list[str] = []
    if style_id:
        ppr_parts.append(f'<w:pStyle w:val="{style_id}"/>')
    if list_item:
        ppr_parts.append('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>')
    ppr_xml = f"<w:pPr>{''.join(ppr_parts)}</w:pPr>" if ppr_parts else ""
    return f"<w:p>{ppr_xml}<w:r><w:t>{text}</w:t></w:r></w:p>"


def _table_xml(style_id: str | None, text: str) -> str:
    return f"<w:tbl><w:tr><w:tc>{_paragraph_xml(style_id, text)}</w:tc></w:tr></w:tbl>"


def _paragraph_style_values(docx: bytes) -> list[str | None]:
    with zipfile.ZipFile(BytesIO(docx)) as package:
        root = ET.fromstring(package.read("word/document.xml"))
    return [attr(style, "val") for style in root.findall(".//w:pPr/w:pStyle", NS)]


def _make_broken_docx() -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("word/document.xml", "<broken>")
    return buffer.getvalue()


def _make_docx_from_document_xml(document_xml: str) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
