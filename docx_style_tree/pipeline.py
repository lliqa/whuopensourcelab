"""DOCX 结构化解析流程说明。"""

from __future__ import annotations

from typing import Any

PARSER_NAME = "ooxml_structure_tree"

PARSER_SUMMARY = (
    "将 DOCX 作为 ZIP 包读取，解析 document.xml 与 styles.xml，"
    "再根据段落属性、样式定义和样式继承关系构建文档结构树。"
)

PROCESSING_PIPELINE: tuple[dict[str, str], ...] = (
    {
        "id": "unpack",
        "name": "解包 DOCX",
        "description": "把 .docx 当作 ZIP 包读取，定位 word/document.xml 与 word/styles.xml。",
    },
    {
        "id": "parse_xml",
        "name": "解析 OOXML",
        "description": "使用 XML 解析器读取正文段落、表格、内容控件和样式定义。",
    },
    {
        "id": "index_styles",
        "name": "建立样式索引",
        "description": "记录 styleId、样式显示名、outlineLvl 和 basedOn 继承链。",
    },
    {
        "id": "classify_blocks",
        "name": "识别结构角色",
        "description": "依据段落属性与样式元数据判断标题层级，并保留普通段落与表格。",
    },
    {
        "id": "build_tree",
        "name": "栈式构建树",
        "description": "按标题层级维护节点栈，把内容块挂到当前章节节点下。",
    },
    {
        "id": "serialize",
        "name": "输出结果",
        "description": "生成 JSON 文档树，并可进一步渲染为 HTML/SVG 或返回 API 响应。",
    },
)


def describe_processing_pipeline() -> dict[str, Any]:
    """@brief 返回解析器名称、摘要和流程步骤。"""
    return {
        "name": PARSER_NAME,
        "summary": PARSER_SUMMARY,
        "pipeline": [dict(step) for step in PROCESSING_PIPELINE],
    }
