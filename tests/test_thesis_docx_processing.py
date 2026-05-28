from __future__ import annotations

import unittest
import zipfile
from io import BytesIO
from typing import Any
from xml.etree import ElementTree as ET

from docx_style_tree import analyze_docx, replace_styles
from docx_style_tree.ooxml import NS, attr, local_name, paragraph_text


class ThesisDocxProcessingTest(unittest.TestCase):
    def test_graduation_thesis_like_docx_builds_expected_tree(self) -> None:
        docx = _make_graduation_thesis_docx()

        result = analyze_docx(docx)

        root = result["tree"]
        self.assertEqual(result["node_count"], 12)
        self.assertEqual(
            [child["title"] for child in root["children"]],
            [
                "摘要",
                "Abstract",
                "目录",
                "第一章 绪论",
                "第二章 系统设计",
                "参考文献",
                "致谢",
                "附录",
            ],
        )
        introduction = _find_node(root, "第一章 绪论")
        assert introduction is not None
        self.assertEqual(
            [child["title"] for child in introduction["children"]],
            ["1.1 研究背景", "1.2 研究意义"],
        )

        background = _find_node(root, "1.1 研究背景")
        assert background is not None
        self.assertEqual(background["content"][1]["type"], "table")
        self.assertEqual(background["content"][1]["rows"][0], ["模块", "说明"])
        self.assertEqual(background["content"][2]["text"], "表 1-1 系统模块说明")

        design = _find_node(root, "第二章 系统设计")
        assert design is not None
        self.assertEqual([child["title"] for child in design["children"]], ["2.1 系统架构"])

    def test_style_replacement_preserves_thesis_package_parts(self) -> None:
        docx = _make_graduation_thesis_docx()

        output = replace_styles(
            docx,
            {
                "heading_1": "Thesis Heading 1",
                "heading_2": "Thesis Heading 2",
                "normal": "Thesis Body",
            },
        )

        original_parts = _read_parts(docx)
        updated_parts = _read_parts(output)
        for part_name in [
            "word/header1.xml",
            "word/footer1.xml",
            "word/footnotes.xml",
            "word/comments.xml",
            "word/numbering.xml",
            "customXml/item1.xml",
        ]:
            self.assertIn(part_name, updated_parts)
            self.assertEqual(updated_parts[part_name], original_parts[part_name])

        document_root = ET.fromstring(updated_parts["word/document.xml"])
        styles_by_text = _paragraph_styles_by_text(document_root)
        self.assertEqual(styles_by_text["摘要"], "ThesisHeading1")
        self.assertEqual(styles_by_text["1.1 研究背景"], "ThesisHeading2")
        self.assertEqual(styles_by_text["摘要正文内容。"], "ThesisBody")
        self.assertEqual(styles_by_text["表 1-1 系统模块说明"], "Caption")

        updated_tags = {local_name(element.tag) for element in document_root.iter()}
        self.assertTrue({"sdt", "hyperlink", "fldSimple"}.issubset(updated_tags))


def _make_graduation_thesis_docx() -> bytes:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    {_paragraph_xml("CoverTitle", "武汉大学本科毕业论文")}
    {_table_xml([["题目", "DOCX 文档结构提取系统"], ["学生", "张三"], ["专业", "软件工程"]])}
    {_toc_sdt_xml()}
    {_paragraph_xml("ThesisHeading1", "摘要")}
    {_paragraph_xml("Normal", "摘要正文内容。")}
    {_paragraph_xml("ThesisHeading1", "Abstract")}
    {_paragraph_xml("Normal", "English abstract body.")}
    {_paragraph_xml("ThesisHeading1", "目录")}
    {_paragraph_xml("ThesisHeading1", "第一章 绪论")}
    {_paragraph_xml("ThesisHeading2", "1.1 研究背景")}
    {_paragraph_xml("Normal", "毕业论文通常包含封面、摘要、目录、正文、参考文献和附录。")}
    {_table_xml([
        ["模块", "说明"],
        ["extractor.py", "提取文档树"],
        ["style_replacer.py", "替换结构样式"],
    ])}
    {_paragraph_xml("Caption", "表 1-1 系统模块说明")}
    {_paragraph_xml("ThesisHeading2", "1.2 研究意义")}
    {_paragraph_xml("Normal", "本节说明项目的课程价值与工程意义。")}
    {_paragraph_xml("ThesisHeading1", "第二章 系统设计")}
    {_paragraph_xml("ThesisHeading2", "2.1 系统架构")}
    {_paragraph_xml("Normal", "系统由 FastAPI 入口、OOXML 解析模块和样式替换模块组成。")}
    {_paragraph_xml("ThesisHeading1", "参考文献")}
    {_paragraph_xml("Normal", "[1] ECMA-376 Office Open XML 标准。", list_item=True)}
    {_paragraph_xml("ThesisHeading1", "致谢")}
    {_paragraph_xml("Normal", "感谢课程教师与小组成员的支持。")}
    {_paragraph_xml("ThesisHeading1", "附录")}
    {_paragraph_xml("Normal", "附录中可放置接口返回 JSON 与测试截图。")}
    <w:sectPr>
      <w:headerReference w:type="default" r:id="rIdHeader1"/>
      <w:footerReference w:type="default" r:id="rIdFooter1"/>
    </w:sectPr>
  </w:body>
</w:document>
"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="CoverTitle">
    <w:name w:val="论文封面题名"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="ThesisHeading1">
    <w:name w:val="标题 1"/>
    <w:pPr><w:outlineLvl w:val="0"/></w:pPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="ThesisHeading2">
    <w:name w:val="标题 2"/>
    <w:pPr><w:outlineLvl w:val="1"/></w:pPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Caption">
    <w:name w:val="Caption"/>
  </w:style>
</w:styles>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
</Types>
"""
    package_rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="word/document.xml"/>
</Relationships>
"""
    document_rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdHeader1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header"
    Target="header1.xml"/>
  <Relationship Id="rIdFooter1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer"
    Target="footer1.xml"/>
</Relationships>
"""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", content_types)
        package.writestr("_rels/.rels", package_rels)
        package.writestr("word/_rels/document.xml.rels", document_rels)
        package.writestr("word/document.xml", document_xml)
        package.writestr("word/styles.xml", styles_xml)
        package.writestr("word/header1.xml", _simple_part_xml("论文页眉"))
        package.writestr("word/footer1.xml", _simple_part_xml("第 1 页"))
        package.writestr("word/footnotes.xml", _simple_part_xml("脚注内容"))
        package.writestr("word/comments.xml", _simple_part_xml("批注内容"))
        package.writestr("word/numbering.xml", _numbering_xml())
        package.writestr(
            "customXml/item1.xml",
            "<metadata><type>graduation-thesis</type></metadata>",
        )
    return buffer.getvalue()


def _paragraph_xml(style_id: str | None, text: str, *, list_item: bool = False) -> str:
    ppr_parts: list[str] = []
    if style_id:
        ppr_parts.append(f'<w:pStyle w:val="{style_id}"/>')
    if list_item:
        ppr_parts.append('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>')
    ppr_xml = f"<w:pPr>{''.join(ppr_parts)}</w:pPr>" if ppr_parts else ""
    return f"<w:p>{ppr_xml}<w:r><w:t>{text}</w:t></w:r></w:p>"


def _table_xml(rows: list[list[str]]) -> str:
    row_xml = []
    for row in rows:
        cells = "".join(f"<w:tc>{_paragraph_xml('Normal', cell)}</w:tc>" for cell in row)
        row_xml.append(f"<w:tr>{cells}</w:tr>")
    return "<w:tbl>" + "".join(row_xml) + "</w:tbl>"


def _toc_sdt_xml() -> str:
    return (
        "<w:sdt><w:sdtContent>"
        '<w:p><w:fldSimple w:instr="TOC \\o &quot;1-3&quot; \\h \\z \\u">'
        "<w:r><w:t>目录域</w:t></w:r>"
        "</w:fldSimple></w:p>"
        f'{_toc_line_xml("第一章 绪论", "3")}'
        f'{_toc_line_xml("第二章 系统设计", "8")}'
        "</w:sdtContent></w:sdt>"
    )


def _toc_line_xml(title: str, page: str) -> str:
    return (
        "<w:p><w:hyperlink r:id=\"rIdToc\">"
        f"<w:r><w:t>{title}</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>{page}</w:t></w:r>"
        "</w:hyperlink></w:p>"
    )


def _simple_part_xml(text: str) -> str:
    return (
        '<w:root xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
        "</w:root>"
    )


def _numbering_xml() -> str:
    return (
        '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:abstractNum w:abstractNumId="0"/>'
        '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
        "</w:numbering>"
    )


def _read_parts(source: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(BytesIO(source)) as package:
        return {info.filename: package.read(info.filename) for info in package.infolist()}


def _paragraph_styles_by_text(document_root: ET.Element) -> dict[str, str | None]:
    styles: dict[str, str | None] = {}
    for paragraph in document_root.findall(".//w:p", NS):
        text = paragraph_text(paragraph)
        if not text:
            continue
        style = paragraph.find("./w:pPr/w:pStyle", NS)
        styles[text] = attr(style, "val") if style is not None else None
    return styles


def _find_node(node: dict[str, Any], title: str) -> dict[str, Any] | None:
    if node["title"] == title:
        return node
    for child in node["children"]:
        result = _find_node(child, title)
        if result is not None:
            return result
    return None


if __name__ == "__main__":
    unittest.main()
