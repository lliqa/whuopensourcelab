"""DOCX Style Tree 的 MCP 工具入口。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docx_style_tree import analyze_docx, describe_processing_pipeline, replace_styles
from docx_style_tree.style_replacer import load_style_map

FastMCPFactory: Any
try:
    from mcp.server.fastmcp import FastMCP as FastMCPFactory
except ImportError:
    FastMCPFactory = None


mcp: Any | None = FastMCPFactory("docx-style-tree") if FastMCPFactory is not None else None


def get_parser_description() -> dict[str, Any]:
    """@brief 返回 DOCX 解析方式和处理流程。"""
    return describe_processing_pipeline()


def analyze_docx_file(path: str) -> dict[str, Any]:
    """@brief 分析本地 DOCX 文件并返回结构树。"""
    input_path = Path(path).expanduser().resolve()
    return analyze_docx(input_path)


def apply_docx_styles_file(
    input_path: str,
    output_path: str,
    style_map_path: str | None = None,
) -> dict[str, Any]:
    """@brief 按结构角色替换 DOCX 样式并写出新文件。"""
    source = Path(input_path).expanduser().resolve()
    target = Path(output_path).expanduser().resolve()
    style_path = Path(style_map_path).expanduser().resolve() if style_map_path else None
    mapping = load_style_map(style_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(replace_styles(source, mapping))
    return {
        "input_path": str(source),
        "output_path": str(target),
        "style_roles": sorted(mapping),
    }


if mcp is not None:

    @mcp.tool()
    def describe_docx_parser() -> dict[str, Any]:
        """说明 DOCX 结构化解析方式和流程。"""
        return get_parser_description()

    @mcp.tool()
    def analyze_docx_path(path: str) -> dict[str, Any]:
        """分析本地 DOCX 文件，返回标题树、段落、表格和样式元数据。"""
        return analyze_docx_file(path)

    @mcp.tool()
    def apply_docx_styles_path(
        input_path: str,
        output_path: str,
        style_map_path: str | None = None,
    ) -> dict[str, Any]:
        """对本地 DOCX 应用结构样式映射，并写出新的 DOCX。"""
        return apply_docx_styles_file(input_path, output_path, style_map_path)


def main() -> None:
    """@brief 启动 MCP server。"""
    if mcp is None:
        raise SystemExit("MCP support is not installed. Run: uv sync --extra mcp")
    mcp.run()


if __name__ == "__main__":
    main()
