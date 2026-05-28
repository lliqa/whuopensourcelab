"""DOCX 结构样式替换。

@author lliqa
@course 武汉大学开源软件与技术课程 2026
"""

from __future__ import annotations

import json
import re
import zipfile
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

from docx_style_tree.errors import InvalidDocxError, InvalidStyleMapError
from docx_style_tree.extractor import detect_heading_level
from docx_style_tree.ooxml import (
    NS,
    ensure_paragraph_style,
    get_paragraph_style,
    local_name,
    normalize_style,
    paragraph_text,
    qn,
)
from docx_style_tree.package import (
    DocxSource,
    parse_xml_part,
    read_required_part,
    read_source,
    read_style_names,
)

DEFAULT_STYLE_MAP = {
    "title": "Title",
    "heading_1": "Heading1",
    "heading_2": "Heading2",
    "heading_3": "Heading3",
    "heading_4": "Heading4",
    "heading_5": "Heading5",
    "heading_6": "Heading6",
    "normal": "Normal",
}

BODY_TEXT_STYLES = {
    "normal",
    "bodytext",
    "bodytextindent",
    "正文",
}


def load_style_map(path: str | Path | None = None) -> dict[str, str]:
    """@brief 从 JSON 加载样式映射，未指定路径时返回默认映射。"""
    if path is None:
        return dict(DEFAULT_STYLE_MAP)
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return normalize_style_map(data)


def replace_styles(
    source: DocxSource,
    style_map: Mapping[str, object] | None = None,
) -> bytes:
    """@brief 替换 DOCX 包中的结构段落样式。

    @param source 输入 DOCX，可以是路径、字节数据或二进制流。
    @param style_map 样式映射，例如 {"heading_1": "Heading 1"}。
    @return 更新后的 DOCX 文件字节数据。
    """
    mapping = normalize_style_map(DEFAULT_STYLE_MAP if style_map is None else style_map)
    docx_bytes = read_source(source)

    styles_xml: bytes | None = None
    try:
        with zipfile.ZipFile(BytesIO(docx_bytes)) as package:
            document_xml = read_required_part(package, "word/document.xml")
            style_names = read_style_names(package)
            try:
                styles_xml = package.read("word/styles.xml")
            except KeyError:
                styles_xml = None
            entries = [(info, package.read(info.filename)) for info in package.infolist()]
    except zipfile.BadZipFile as exc:
        raise InvalidDocxError("Input is not a valid DOCX archive.") from exc

    style_lookup = _build_style_lookup(style_names)
    document_root = parse_xml_part(document_xml, "word/document.xml")
    styles_root = (
        parse_xml_part(styles_xml, "word/styles.xml") if styles_xml else _new_styles_root()
    )
    document_changed, styles_changed = _replace_document_styles(
        document_root,
        style_names,
        style_lookup,
        styles_root,
        mapping,
    )
    updated_document_xml = ET.tostring(document_root, encoding="utf-8", xml_declaration=True)
    updated_styles_xml = ET.tostring(styles_root, encoding="utf-8", xml_declaration=True)

    output = BytesIO()
    wrote_styles = False
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for info, content in entries:
            new_info = _copy_zip_info(info)
            if info.filename == "word/styles.xml":
                wrote_styles = True
            package.writestr(
                new_info,
                _replacement_content(
                    info.filename,
                    content,
                    updated_document_xml,
                    updated_styles_xml,
                    document_changed,
                    styles_changed,
                ),
            )
        if styles_changed and not wrote_styles:
            package.writestr("word/styles.xml", updated_styles_xml)

    return output.getvalue()


def normalize_style_map(style_map: Mapping[str, object]) -> dict[str, str]:
    """@brief 校验并规范化用户提供的样式映射。"""
    if not isinstance(style_map, Mapping):
        raise InvalidStyleMapError("style_map must be a JSON object.")

    mapping: dict[str, str] = {}
    for key, value in style_map.items():
        if not isinstance(key, str) or not key.strip():
            raise InvalidStyleMapError("style_map keys must be non-empty strings.")
        if not isinstance(value, str) or not value.strip():
            raise InvalidStyleMapError(f'style_map value for "{key}" must be a non-empty string.')
        mapping[key.strip()] = value.strip()
    return mapping


def _replace_document_styles(
    document_root: ET.Element,
    style_names: dict[str, str],
    style_lookup: dict[str, str],
    styles_root: ET.Element,
    mapping: dict[str, str],
) -> tuple[bool, bool]:
    """@brief 将样式映射应用到每个结构段落。"""
    body = document_root.find(".//w:body", NS)
    if body is None:
        return False, False

    document_changed = False
    styles_changed = False
    for paragraph in body:
        if local_name(paragraph.tag) != "p" or _is_list_paragraph(paragraph):
            continue

        text = paragraph_text(paragraph)
        if not text:
            continue

        style_id = get_paragraph_style(paragraph)
        style_name = style_names.get(style_id or "")
        level = detect_heading_level(paragraph, style_id, style_name)
        key = _mapping_key(level, style_id, style_name)
        if key is None or key not in mapping:
            continue

        target_style, target_created = _resolve_style_id(
            key,
            mapping[key],
            style_lookup,
            styles_root,
        )
        styles_changed = styles_changed or target_created
        if not target_style or target_style == style_id:
            continue

        style_node = ensure_paragraph_style(paragraph)
        style_node.set(qn("val"), target_style)
        document_changed = True
    return document_changed, styles_changed


def _mapping_key(level: int | None, style_id: str | None, style_name: str | None) -> str | None:
    """@brief 将段落样式分类转换为 style map 键。"""
    normalized_values = {normalize_style(value) for value in [style_id, style_name] if value}
    if "title" in normalized_values:
        return "title"
    if level is not None:
        return f"heading_{level}"
    if normalized_values & BODY_TEXT_STYLES:
        return "normal"
    return None


def _is_list_paragraph(paragraph: ET.Element) -> bool:
    """@brief 判断段落是否属于编号或项目符号列表。"""
    return paragraph.find("./w:pPr/w:numPr", NS) is not None


def _build_style_lookup(style_names: dict[str, str]) -> dict[str, str]:
    """@brief 构建规范化样式 ID 或名称到样式 ID 的查找表。"""
    lookup: dict[str, str] = {}
    for style_id, style_name in style_names.items():
        lookup[normalize_style(style_id)] = style_id
        lookup[normalize_style(style_name)] = style_id
    return lookup


def _resolve_style_id(
    key: str,
    target: str,
    style_lookup: dict[str, str],
    styles_root: ET.Element,
) -> tuple[str, bool]:
    """@brief 将可读样式名称解析为 DOCX 样式 ID。"""
    style_id = style_lookup.get(normalize_style(target))
    if style_id is not None:
        return style_id, False

    style_id = _style_id_from_target(key, target)
    _append_paragraph_style(styles_root, style_id, target, key, style_lookup)
    style_lookup[normalize_style(style_id)] = style_id
    style_lookup[normalize_style(target)] = style_id
    return style_id, True


def _style_id_from_target(key: str, target: str) -> str:
    """@brief 根据映射目标构造合法的 Word 样式 ID。"""
    style_id = re.sub(r"[^A-Za-z0-9_]", "", target)
    if not style_id:
        style_id = "".join(part.capitalize() for part in key.split("_"))
    if style_id[0].isdigit():
        style_id = f"Style{style_id}"
    return style_id


def _append_paragraph_style(
    styles_root: ET.Element,
    style_id: str,
    style_name: str,
    key: str,
    style_lookup: dict[str, str],
) -> None:
    """@brief 向 styles.xml 追加最小段落样式定义。"""
    style = ET.SubElement(
        styles_root, qn("style"), {qn("type"): "paragraph", qn("styleId"): style_id}
    )
    ET.SubElement(style, qn("name")).set(qn("val"), style_name)

    base_style = style_lookup.get("normal")
    if base_style:
        ET.SubElement(style, qn("basedOn")).set(qn("val"), base_style)
        ET.SubElement(style, qn("next")).set(qn("val"), base_style)

    level = _heading_level_from_key(key)
    if level is not None:
        ppr = ET.SubElement(style, qn("pPr"))
        ET.SubElement(ppr, qn("outlineLvl")).set(qn("val"), str(level - 1))
        rpr = ET.SubElement(style, qn("rPr"))
        ET.SubElement(rpr, qn("b"))
        ET.SubElement(rpr, qn("sz")).set(qn("val"), str(max(20, 36 - (level - 1) * 4)))

    ET.SubElement(style, qn("qFormat"))


def _heading_level_from_key(key: str) -> int | None:
    """@brief 将 heading_N 键解析为标题层级。"""
    match = re.fullmatch(r"heading_([1-9])", key)
    return int(match.group(1)) if match else None


def _new_styles_root() -> ET.Element:
    """@brief 在 DOCX 缺少 styles.xml 时创建最小 styles 根节点。"""
    return ET.Element(qn("styles"))


def _replacement_content(
    filename: str,
    original_content: bytes,
    updated_document_xml: bytes,
    updated_styles_xml: bytes,
    document_changed: bool,
    styles_changed: bool,
) -> bytes:
    """@brief 为 DOCX 包成员选择替换后的内容。"""
    if filename == "word/document.xml" and document_changed:
        return updated_document_xml
    if filename == "word/styles.xml" and styles_changed:
        return updated_styles_xml
    return original_content


def _copy_zip_info(info: zipfile.ZipInfo) -> zipfile.ZipInfo:
    """@brief 复制未改动 DOCX ZIP 成员的元数据。"""
    new_info = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
    new_info.comment = info.comment
    new_info.compress_type = info.compress_type
    new_info.create_system = info.create_system
    new_info.external_attr = info.external_attr
    new_info.extra = info.extra
    new_info.internal_attr = info.internal_attr
    return new_info
