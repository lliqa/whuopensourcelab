"""Office Open XML 通用辅助函数。

@author lliqa
@course 武汉大学开源软件与技术课程 2026
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W_NS, "r": R_NS}

ET.register_namespace("w", W_NS)
ET.register_namespace("r", R_NS)

BODY_BLOCK_TAGS = {"p", "tbl"}
TRANSPARENT_BLOCK_CONTAINERS = {
    "body",
    "customXml",
    "ins",
    "moveFrom",
    "moveTo",
    "sdt",
    "sdtContent",
    "smartTag",
}


@dataclass(frozen=True)
class BodyBlock:
    """@brief 文档正文中按顺序遍历得到的块级元素。"""

    element: ET.Element
    tag: str
    index: int
    container_path: tuple[str, ...]


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


def iter_body_blocks(body: ET.Element) -> Iterator[BodyBlock]:
    """@brief 按正文顺序遍历段落、表格和透明容器中的块级元素。

    DOCX 中的段落和表格不一定都是 `w:body` 的直接子元素，真实模板中常见
    `w:sdt` 内容控件、`w:ins` 插入修订、`w:customXml` 等透明容器。本函数
    将这些容器展开，向调用者提供稳定的块级遍历结果。
    """
    for index, (element, tag, path) in enumerate(_iter_block_elements(body, ())):
        yield BodyBlock(element=element, tag=tag, index=index, container_path=path)


def _iter_block_elements(
    parent: ET.Element,
    container_path: tuple[str, ...],
) -> Iterator[tuple[ET.Element, str, tuple[str, ...]]]:
    """@brief 递归展开 OOXML 透明块级容器。"""
    for child in parent:
        tag = local_name(child.tag)
        if tag in BODY_BLOCK_TAGS:
            yield child, tag, container_path
        elif tag in TRANSPARENT_BLOCK_CONTAINERS:
            if tag == "sdt" and contains_toc_field(child):
                continue
            yield from _iter_block_elements(child, container_path + (tag,))


def contains_toc_field(element: ET.Element) -> bool:
    """@brief 判断元素内部是否包含目录域。"""
    for descendant in element.iter():
        tag = local_name(descendant.tag)
        if tag == "fldSimple":
            instruction = attr(descendant, "instr")
        elif tag == "instrText":
            instruction = descendant.text
        else:
            instruction = None

        if instruction and _is_toc_instruction(instruction):
            return True
    return False


def _is_toc_instruction(instruction: str) -> bool:
    """@brief 判断域指令是否为 TOC 目录。"""
    normalized = instruction.strip().upper()
    return normalized == "TOC" or normalized.startswith("TOC ")


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
