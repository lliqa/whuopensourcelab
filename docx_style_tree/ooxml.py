"""Office Open XML 通用辅助函数。

@author lliqa
@course 武汉大学开源软件与技术课程 2026
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
    """@brief 构造 WordprocessingML 限定名。"""
    return f"{{{W_NS}}}{name}"


def attr(element: ET.Element, name: str) -> str | None:
    """@brief 读取 WordprocessingML 属性值。"""
    return element.get(qn(name))


def local_name(tag: str) -> str:
    """@brief 返回去除命名空间后的 XML 标签名。"""
    return tag.rsplit("}", 1)[-1]


def normalize_style(value: str | None) -> str:
    """@brief 规范化样式 ID 和名称，便于宽松匹配。"""
    if not value:
        return ""
    return re.sub(r"[\s_\-]+", "", value).lower()


def paragraph_text(paragraph: ET.Element) -> str:
    """@brief 从段落元素中提取可见文本。"""
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
    """@brief 返回段落样式 ID。"""
    style = paragraph.find("./w:pPr/w:pStyle", NS)
    return attr(style, "val") if style is not None else None


def ensure_paragraph_style(paragraph: ET.Element) -> ET.Element:
    """@brief 确保段落包含 pPr/pStyle 元素。"""
    ppr = paragraph.find("./w:pPr", NS)
    if ppr is None:
        ppr = ET.Element(qn("pPr"))
        paragraph.insert(0, ppr)

    style = ppr.find("./w:pStyle", NS)
    if style is None:
        style = ET.Element(qn("pStyle"))
        ppr.insert(0, style)
    return style
