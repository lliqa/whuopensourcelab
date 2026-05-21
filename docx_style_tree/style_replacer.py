"""DOCX structural style replacement.

@author lliqa
@course Wuhan University Open Source Software and Technology 2026
"""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from xml.etree import ElementTree as ET

from docx_style_tree.extractor import DocxSource, _read_source, _read_style_names, detect_heading_level
from docx_style_tree.ooxml import (
    NS,
    attr,
    ensure_paragraph_style,
    get_paragraph_style,
    normalize_style,
    paragraph_text,
    qn,
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


def load_style_map(path: str | Path | None = None) -> dict[str, str]:
    """@brief Load style mapping from JSON or return the default mapping."""
    if path is None:
        return dict(DEFAULT_STYLE_MAP)
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(key): str(value) for key, value in data.items()}


def replace_styles(
    source: DocxSource,
    style_map: dict[str, str] | None = None,
) -> bytes:
    """@brief Replace structural paragraph styles in a DOCX package.

    @param source Input DOCX as path, bytes, or binary stream.
    @param style_map Mapping such as {"heading_1": "Heading 1"}.
    @return Bytes of the updated DOCX file.
    """
    mapping = style_map or DEFAULT_STYLE_MAP
    docx_bytes = _read_source(source)

    with zipfile.ZipFile(BytesIO(docx_bytes)) as package:
        document_xml = package.read("word/document.xml")
        style_names = _read_style_names(package)
        entries = {info.filename: (info, package.read(info.filename)) for info in package.infolist()}

    style_lookup = _build_style_lookup(style_names)
    document_root = ET.fromstring(document_xml)
    changed = _replace_document_styles(document_root, style_names, style_lookup, mapping)
    updated_document_xml = ET.tostring(document_root, encoding="utf-8", xml_declaration=True)

    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for filename, (info, content) in entries.items():
            new_info = zipfile.ZipInfo(filename=filename, date_time=info.date_time)
            new_info.external_attr = info.external_attr
            new_info.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(
                new_info,
                updated_document_xml if filename == "word/document.xml" and changed else content,
            )

    return output.getvalue()


def _replace_document_styles(
    document_root: ET.Element,
    style_names: dict[str, str],
    style_lookup: dict[str, str],
    mapping: dict[str, str],
) -> bool:
    """@brief Apply style mapping to each structural paragraph."""
    changed = False
    for paragraph in document_root.findall(".//w:p", NS):
        text = paragraph_text(paragraph)
        if not text:
            continue

        style_id = get_paragraph_style(paragraph)
        style_name = style_names.get(style_id or "")
        level = detect_heading_level(paragraph, style_id, style_name)
        key = _mapping_key(level, style_id, style_name)
        if key is None or key not in mapping:
            continue

        target_style = _resolve_style_id(mapping[key], style_lookup)
        if not target_style or target_style == style_id:
            continue

        style_node = ensure_paragraph_style(paragraph)
        style_node.set(qn("val"), target_style)
        changed = True
    return changed


def _mapping_key(level: int | None, style_id: str | None, style_name: str | None) -> str | None:
    """@brief Convert a paragraph style classification to a style map key."""
    normalized = normalize_style(" ".join(value for value in [style_id, style_name] if value))
    if normalized == "title":
        return "title"
    if level is not None:
        return f"heading_{level}"
    if style_id or style_name:
        return "normal"
    return None


def _build_style_lookup(style_names: dict[str, str]) -> dict[str, str]:
    """@brief Build normalized style id/name to style id lookup table."""
    lookup: dict[str, str] = {}
    for style_id, style_name in style_names.items():
        lookup[normalize_style(style_id)] = style_id
        lookup[normalize_style(style_name)] = style_id
    return lookup


def _resolve_style_id(target: str, style_lookup: dict[str, str]) -> str:
    """@brief Resolve a human-readable style name to a DOCX style id."""
    return style_lookup.get(normalize_style(target), target)
