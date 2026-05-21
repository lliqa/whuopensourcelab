"""DOCX package input and XML helpers.

@author lliqa
@course Wuhan University Open Source Software and Technology 2026
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
    """@brief Normalize supported input sources to bytes."""
    if isinstance(source, bytes):
        return source
    if isinstance(source, (str, Path)):
        return Path(source).read_bytes()

    data = source.read()
    if not isinstance(data, bytes):
        raise TypeError("DOCX source file-like object must return bytes.")
    return data


def read_required_part(package: zipfile.ZipFile, part_name: str) -> bytes:
    """@brief Read a required DOCX part or raise a domain error."""
    try:
        return package.read(part_name)
    except KeyError as exc:
        raise InvalidDocxError(f"DOCX is missing required part: {part_name}.") from exc


def parse_xml_part(content: bytes, part_name: str) -> ET.Element:
    """@brief Parse an OOXML part and report malformed XML as invalid DOCX."""
    try:
        return ET.fromstring(content)
    except ET.ParseError as exc:
        raise InvalidDocxError(f"DOCX part {part_name} is not valid XML.") from exc


def read_style_names(package: zipfile.ZipFile) -> dict[str, str]:
    """@brief Read paragraph style id to display name mappings from styles.xml."""
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
