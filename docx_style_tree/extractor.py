"""DOCX structure extraction.

@author lliqa
@course Wuhan University Open Source Software and Technology 2026
"""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO
from xml.etree import ElementTree as ET

from docx_style_tree.models import DocumentNode
from docx_style_tree.ooxml import (
    NS,
    attr,
    get_paragraph_style,
    local_name,
    normalize_style,
    paragraph_text,
)

DocxSource = str | Path | bytes | BinaryIO

CHINESE_LEVELS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def analyze_docx(source: DocxSource) -> dict[str, Any]:
    """@brief Analyze a DOCX file and return a document tree.

    @param source File path, bytes, or a binary file-like object.
    @return JSON-ready dictionary containing metadata and tree data.
    """
    docx_bytes = _read_source(source)
    with zipfile.ZipFile(BytesIO(docx_bytes)) as package:
        document_xml = package.read("word/document.xml")
        style_names = _read_style_names(package)

    root = ET.fromstring(document_xml)
    tree = _build_tree(root, style_names)
    return {
        "format": "docx",
        "node_count": _count_nodes(tree),
        "tree": tree.to_dict(),
    }


def _read_source(source: DocxSource) -> bytes:
    """@brief Normalize supported input sources to bytes."""
    if isinstance(source, bytes):
        return source
    if isinstance(source, (str, Path)):
        return Path(source).read_bytes()
    return source.read()


def _read_style_names(package: zipfile.ZipFile) -> dict[str, str]:
    """@brief Read style id to display name mappings from styles.xml."""
    try:
        styles_xml = package.read("word/styles.xml")
    except KeyError:
        return {}

    root = ET.fromstring(styles_xml)
    names: dict[str, str] = {}
    for style in root.findall(".//w:style", NS):
        style_id = attr(style, "styleId")
        name_node = style.find("./w:name", NS)
        style_name = attr(name_node, "val") if name_node is not None else None
        if style_id and style_name:
            names[style_id] = style_name
    return names


def _build_tree(document_root: ET.Element, style_names: dict[str, str]) -> DocumentNode:
    """@brief Build a heading-based tree from the document body."""
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
            level = detect_heading_level(child, style_id, style_name)
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
) -> int | None:
    """@brief Detect whether a paragraph is a heading and return its level."""
    outline = paragraph.find("./w:pPr/w:outlineLvl", NS)
    outline_value = attr(outline, "val") if outline is not None else None
    if outline_value is not None and outline_value.isdigit():
        return int(outline_value) + 1

    combined = " ".join(value for value in [style_id, style_name] if value)
    normalized = normalize_style(combined)

    match = re.search(r"heading([1-9])", normalized)
    if match:
        return int(match.group(1))

    match = re.search(r"标题([1-9一二三四五六七八九])", combined)
    if match:
        value = match.group(1)
        return int(value) if value.isdigit() else CHINESE_LEVELS[value]

    if normalized in {"title", "biaoti"}:
        return 1
    return _detect_text_heading_level(paragraph_text(paragraph))


def _detect_text_heading_level(text: str) -> int | None:
    """@brief Detect plain-text headings when DOCX styles are missing."""
    compact = re.sub(r"\s+", "", text)
    if not compact:
        return None

    if re.match(r"^第[一二三四五六七八九十百]+[、.．]", compact):
        return 1

    normalized_title = compact.rstrip("、:：")
    if normalized_title == "习题解析":
        return 2
    question_titles = {"单选题", "多选题", "判断题", "填空题", "简答题"}
    if normalized_title in question_titles:
        return 3
    return None


def _extract_table(table: ET.Element) -> dict[str, Any]:
    """@brief Extract table text as row and cell data."""
    rows: list[list[str]] = []
    for row in table.findall("./w:tr", NS):
        cells: list[str] = []
        for cell in row.findall("./w:tc", NS):
            paragraphs = [paragraph_text(p) for p in cell.findall(".//w:p", NS)]
            cells.append("\n".join(text for text in paragraphs if text))
        rows.append(cells)
    return {"type": "table", "rows": rows}


def _count_nodes(node: DocumentNode) -> int:
    """@brief Count the root and all descendants."""
    return 1 + sum(_count_nodes(child) for child in node.children)
