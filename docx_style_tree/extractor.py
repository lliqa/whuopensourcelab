"""DOCX 文档结构提取。

@author lliqa
@course 武汉大学开源软件与技术课程 2026
"""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from typing import Any
from xml.etree import ElementTree as ET

from docx_style_tree.errors import InvalidDocxError
from docx_style_tree.models import DocumentNode
from docx_style_tree.ooxml import (
    NS,
    attr,
    get_paragraph_style,
    local_name,
    normalize_style,
    paragraph_text,
)
from docx_style_tree.package import (
    DocxSource,
    parse_xml_part,
    read_required_part,
    read_source,
    read_style_names,
    read_style_outline_levels,
)

CHINESE_NUMERAL_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
CHINESE_NUMERAL_UNITS = {
    "十": 10,
    "百": 100,
    "千": 1000,
}
CHINESE_NUMERAL_CHARS = "".join(CHINESE_NUMERAL_DIGITS) + "".join(CHINESE_NUMERAL_UNITS)

STYLE_HEADING_RE = re.compile(rf"标题\s*([1-9{CHINESE_NUMERAL_CHARS}]+)")


def analyze_docx(source: DocxSource) -> dict[str, Any]:
    """@brief 分析 DOCX 文件并返回文档树。

    @param source 文件路径、字节数据或二进制文件对象。
    @return 包含元数据和文档树的 JSON 可序列化字典。
    """
    docx_bytes = read_source(source)
    try:
        with zipfile.ZipFile(BytesIO(docx_bytes)) as package:
            document_xml = read_required_part(package, "word/document.xml")
            style_names = read_style_names(package)
            style_outline_levels = read_style_outline_levels(package)
    except zipfile.BadZipFile as exc:
        raise InvalidDocxError("Input is not a valid DOCX archive.") from exc

    root = parse_xml_part(document_xml, "word/document.xml")
    tree = _build_tree(root, style_names, style_outline_levels)
    return {
        "format": "docx",
        "node_count": _count_nodes(tree),
        "tree": tree.to_dict(),
    }


def _build_tree(
    document_root: ET.Element,
    style_names: dict[str, str],
    style_outline_levels: dict[str, int],
) -> DocumentNode:
    """@brief 根据文档正文中的标题构建层级树。"""
    body = document_root.find(".//w:body", NS)
    root = DocumentNode(title="Document", level=0)
    stack = [root]
    if body is None:
        return root

    for child in body:
        tag = local_name(child.tag)
        if tag == "p":
            text = paragraph_text(child)
            if not text:
                continue
            style_id = get_paragraph_style(child)
            style_name = style_names.get(style_id or "")
            style_outline_level = style_outline_levels.get(style_id or "")
            level = detect_heading_level(child, style_id, style_name, style_outline_level)
            if level is not None:
                node = DocumentNode(
                    title=text,
                    level=level,
                    style_id=style_id,
                    style_name=style_name,
                )
                while stack and stack[-1].level >= level:
                    stack.pop()
                stack[-1].children.append(node)
                stack.append(node)
                continue

            stack[-1].content.append(
                {
                    "type": "paragraph",
                    "text": text,
                    "style_id": style_id,
                    "style_name": style_name,
                }
            )
        elif tag == "tbl":
            stack[-1].content.append(_extract_table(child))

    return root


def detect_heading_level(
    paragraph: ET.Element,
    style_id: str | None,
    style_name: str | None,
    style_outline_level: int | None = None,
) -> int | None:
    """@brief 判断段落是否为标题，并返回标题层级。"""
    outline = paragraph.find("./w:pPr/w:outlineLvl", NS)
    outline_value = attr(outline, "val") if outline is not None else None
    if outline_value is not None and outline_value.isdigit():
        return int(outline_value) + 1
    if style_outline_level is not None:
        return style_outline_level

    combined = " ".join(value for value in [style_id, style_name] if value)
    normalized = normalize_style(combined)

    match = re.search(r"heading([1-9])", normalized)
    if match:
        return int(match.group(1))

    match = STYLE_HEADING_RE.search(combined)
    if match:
        level = _coerce_heading_level(match.group(1))
        if level is not None:
            return level

    if normalized in {"title", "biaoti"}:
        return 1
    return None


def _coerce_heading_level(value: str) -> int | None:
    """@brief 将数字或中文数字转换为有效标题层级。"""
    if value.isdigit():
        level = int(value)
    else:
        parsed = _parse_chinese_number(value)
        if parsed is None:
            return None
        level = parsed
    return level if 1 <= level <= 9 else None


def _parse_chinese_number(value: str) -> int | None:
    """@brief 解析简单中文数字。"""
    total = 0
    current = 0
    for char in value:
        if char in CHINESE_NUMERAL_DIGITS:
            current = CHINESE_NUMERAL_DIGITS[char]
            continue
        unit = CHINESE_NUMERAL_UNITS.get(char)
        if unit is None:
            return None
        total += (current or 1) * unit
        current = 0

    result = total + current
    return result if result > 0 else None


def _extract_table(table: ET.Element) -> dict[str, Any]:
    """@brief 将表格文本提取为行和单元格数据。"""
    rows: list[list[str]] = []
    for row in table.findall("./w:tr", NS):
        cells: list[str] = []
        for cell in row.findall("./w:tc", NS):
            paragraphs = [paragraph_text(p) for p in cell.findall(".//w:p", NS)]
            cells.append("\n".join(text for text in paragraphs if text))
        rows.append(cells)
    return {"type": "table", "rows": rows}


def _count_nodes(node: DocumentNode) -> int:
    """@brief 统计根节点及其所有子孙节点数量。"""
    return 1 + sum(_count_nodes(child) for child in node.children)
