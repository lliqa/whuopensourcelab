"""Small Office Open XML helpers.

@author lliqa
@course Wuhan University Open Source Software and Technology 2026
"""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W_NS, "r": R_NS}

ET.register_namespace("w", W_NS)
ET.register_namespace("r", R_NS)


def qn(name: str) -> str:
    """@brief Build a WordprocessingML qualified name."""
    return f"{{{W_NS}}}{name}"


def attr(element: ET.Element, name: str) -> str | None:
    """@brief Read a WordprocessingML attribute value."""
    return element.get(qn(name))


def local_name(tag: str) -> str:
    """@brief Return an XML tag name without namespace."""
    return tag.rsplit("}", 1)[-1]


def normalize_style(value: str | None) -> str:
    """@brief Normalize style ids and names for loose matching."""
    if not value:
        return ""
    return re.sub(r"[\s_\-]+", "", value).lower()


def paragraph_text(paragraph: ET.Element) -> str:
    """@brief Extract visible text from a paragraph element."""
    parts: list[str] = []
    for node in paragraph.iter():
        name = local_name(node.tag)
        if name == "t" and node.text:
            parts.append(node.text)
        elif name == "tab":
            parts.append("\t")
        elif name in {"br", "cr"}:
            parts.append("\n")
    return "".join(parts).strip()


def get_paragraph_style(paragraph: ET.Element) -> str | None:
    """@brief Return the paragraph style id."""
    style = paragraph.find("./w:pPr/w:pStyle", NS)
    return attr(style, "val") if style is not None else None


def ensure_paragraph_style(paragraph: ET.Element) -> ET.Element:
    """@brief Ensure that a paragraph has a pPr/pStyle element."""
    ppr = paragraph.find("./w:pPr", NS)
    if ppr is None:
        ppr = ET.Element(qn("pPr"))
        paragraph.insert(0, ppr)

    style = ppr.find("./w:pStyle", NS)
    if style is None:
        style = ET.Element(qn("pStyle"))
        ppr.insert(0, style)
    return style
