"""DOCX 包输入与 XML 解析辅助函数。

@author lliqa
@course 武汉大学开源软件与技术课程 2026
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import BinaryIO
from xml.etree import ElementTree as ET

from docx_style_tree.errors import InvalidDocxError
from docx_style_tree.ooxml import NS, attr

DocxSource = str | Path | bytes | BinaryIO


def read_source(source: DocxSource) -> bytes:
    """@brief 将支持的输入来源统一读取为字节数据。"""
    if isinstance(source, bytes):
        return source
    if isinstance(source, str | Path):
        return Path(source).read_bytes()

    data = source.read()
    if not isinstance(data, bytes):
        raise TypeError("DOCX source file-like object must return bytes.")
    return data


def read_required_part(package: zipfile.ZipFile, part_name: str) -> bytes:
    """@brief 读取必需的 DOCX 部件，缺失时抛出领域异常。"""
    try:
        return package.read(part_name)
    except KeyError as exc:
        raise InvalidDocxError(f"DOCX is missing required part: {part_name}.") from exc


def parse_xml_part(content: bytes, part_name: str) -> ET.Element:
    """@brief 解析 OOXML 部件，并将格式错误的 XML 报告为无效 DOCX。"""
    try:
        return ET.fromstring(content)
    except ET.ParseError as exc:
        raise InvalidDocxError(f"DOCX part {part_name} is not valid XML.") from exc


def read_style_names(package: zipfile.ZipFile) -> dict[str, str]:
    """@brief 从 styles.xml 读取段落样式 ID 到显示名称的映射。"""
    try:
        styles_xml = package.read("word/styles.xml")
    except KeyError:
        return {}

    root = parse_xml_part(styles_xml, "word/styles.xml")
    names: dict[str, str] = {}
    for style in root.findall(".//w:style", NS):
        if attr(style, "type") != "paragraph":
            continue
        style_id = attr(style, "styleId")
        name_node = style.find("./w:name", NS)
        style_name = attr(name_node, "val") if name_node is not None else None
        if style_id and style_name:
            names[style_id] = style_name
    return names


def read_style_outline_levels(package: zipfile.ZipFile) -> dict[str, int]:
    """@brief 从 styles.xml 读取段落样式 ID 到标题层级的映射。"""
    try:
        styles_xml = package.read("word/styles.xml")
    except KeyError:
        return {}

    root = parse_xml_part(styles_xml, "word/styles.xml")
    direct_levels: dict[str, int] = {}
    based_on: dict[str, str] = {}
    for style in root.findall(".//w:style", NS):
        if attr(style, "type") != "paragraph":
            continue
        style_id = attr(style, "styleId")
        if not style_id:
            continue

        outline = style.find("./w:pPr/w:outlineLvl", NS)
        outline_value = attr(outline, "val") if outline is not None else None
        if outline_value is not None and outline_value.isdigit():
            direct_levels[style_id] = int(outline_value) + 1

        based_on_node = style.find("./w:basedOn", NS)
        parent_id = attr(based_on_node, "val") if based_on_node is not None else None
        if parent_id:
            based_on[style_id] = parent_id

    resolved: dict[str, int] = {}
    for style_id in set(direct_levels) | set(based_on):
        level = _resolve_style_outline_level(style_id, direct_levels, based_on, set())
        if level is not None:
            resolved[style_id] = level
    return resolved


def _resolve_style_outline_level(
    style_id: str,
    direct_levels: dict[str, int],
    based_on: dict[str, str],
    visiting: set[str],
) -> int | None:
    """@brief 解析样式自身或其 basedOn 祖先定义的标题层级。"""
    if style_id in direct_levels:
        return direct_levels[style_id]
    if style_id in visiting:
        return None

    parent_id = based_on.get(style_id)
    if parent_id is None:
        return None
    visiting.add(style_id)
    return _resolve_style_outline_level(parent_id, direct_levels, based_on, visiting)
