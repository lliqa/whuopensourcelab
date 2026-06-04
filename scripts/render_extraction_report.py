"""生成 DOCX 结构提取结果的可视化演示报告。

@author lliqa
@course 武汉大学开源软件与技术课程 2026
"""

from __future__ import annotations

import argparse
import json
import textwrap
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from docx_style_tree import analyze_docx

NodeDict = dict[str, Any]

NODE_COLORS = {
    0: ("#f1f5f9", "#64748b"),
    1: ("#dbeafe", "#2563eb"),
    2: ("#dcfce7", "#16a34a"),
    3: ("#fef3c7", "#d97706"),
    4: ("#fae8ff", "#9333ea"),
}


@dataclass(frozen=True)
class PositionedNode:
    """@brief 带有 SVG 坐标的文档树节点。"""

    index: int
    parent_index: int | None
    title: str
    level: int
    depth: int
    x: int
    y: int
    style_id: str | None
    style_name: str | None
    detect_reason: str | None
    paragraph_count: int
    table_count: int


def main() -> None:
    """@brief 解析命令行参数并生成报告文件。"""
    parser = argparse.ArgumentParser(description="Render a visual DOCX extraction report.")
    parser.add_argument("input", type=Path, help="input .docx file")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("outputs/extraction-report"),
        help="directory for tree.json, tree.svg and index.html",
    )
    args = parser.parse_args()
    render_report(args.input, args.output_dir)


def render_report(input_path: Path, output_dir: Path) -> None:
    """@brief 分析 DOCX 文件并输出 JSON、SVG 和 HTML 报告。"""
    result = analyze_docx(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    tree_json = output_dir / "tree.json"
    tree_svg = output_dir / "tree.svg"
    index_html = output_dir / "index.html"

    tree_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tree_svg.write_text(_render_svg(result["tree"]), encoding="utf-8")
    index_html.write_text(_render_html(input_path, result), encoding="utf-8")

    print(f"Wrote extraction report to {index_html}")
    print(f"Wrote tree SVG to {tree_svg}")
    print(f"Wrote raw tree JSON to {tree_json}")


def _render_html(input_path: Path, result: NodeDict) -> str:
    """@brief 生成适合演示截图的 HTML 报告。"""
    tree = result["tree"]
    tree_markup = _render_tree_details(tree)
    filename = escape(input_path.name)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DOCX 结构提取可视化报告</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172033;
      --muted: #667085;
      --line: #d0d7de;
      --panel: #ffffff;
      --paper: #f6f8fb;
      --blue: #2563eb;
      --green: #16a34a;
      --amber: #d97706;
      --red: #dc2626;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      padding: 28px 40px 20px;
      background: #ffffff;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      line-height: 1.18;
      letter-spacing: 0;
    }}
    .subtitle {{
      margin: 0;
      color: var(--muted);
      font-size: 15px;
    }}
    main {{
      padding: 28px 40px 48px;
      display: grid;
      gap: 24px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(160px, 1fr));
      gap: 14px;
    }}
    .metric, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .metric {{
      padding: 16px 18px;
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }}
    .metric strong {{
      font-size: 28px;
      line-height: 1;
    }}
    .grid {{
      display: grid;
      grid-template-columns: minmax(360px, 0.95fr) minmax(480px, 1.35fr);
      gap: 24px;
      align-items: start;
    }}
    .panel {{
      padding: 20px;
      overflow: auto;
    }}
    h2 {{
      margin: 0 0 16px;
      font-size: 20px;
      letter-spacing: 0;
    }}
    .pipeline {{
      display: grid;
      grid-template-columns: repeat(5, minmax(128px, 1fr));
      gap: 10px;
    }}
    .step {{
      border: 1px solid var(--line);
      border-left: 4px solid var(--blue);
      border-radius: 8px;
      padding: 12px;
      background: #fbfdff;
      min-height: 88px;
    }}
    .step b {{
      display: block;
      margin-bottom: 6px;
    }}
    .step span {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .note {{
      border-left: 4px solid var(--green);
      padding: 12px 14px;
      background: #f0fdf4;
      border-radius: 6px;
      color: #14532d;
      line-height: 1.65;
    }}
    .explain {{
      margin: 0 0 14px;
      color: var(--muted);
      line-height: 1.7;
    }}
    .algorithm {{
      margin: 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(5, minmax(128px, 1fr));
      gap: 10px;
      list-style: none;
    }}
    .algorithm li {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fbfdff;
    }}
    .algorithm b {{
      display: block;
      margin-bottom: 6px;
    }}
    .algorithm span {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .pseudo {{
      margin: 16px 0 0;
      padding: 14px 16px;
      background: #111827;
      color: #d1d5db;
      border-radius: 8px;
      overflow: auto;
      font-size: 13px;
      line-height: 1.55;
    }}
    .api-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(180px, 1fr));
      gap: 10px;
    }}
    .api-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fbfdff;
    }}
    .api-card b {{
      display: block;
      margin-bottom: 6px;
      color: var(--blue);
    }}
    .api-card span {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    details {{
      border-left: 2px solid var(--line);
      margin-left: 10px;
      padding-left: 14px;
    }}
    details details {{
      margin-top: 10px;
    }}
    summary {{
      cursor: default;
      list-style: none;
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      margin: 8px 0;
      font-weight: 650;
    }}
    summary::-webkit-details-marker {{ display: none; }}
    .level {{
      min-width: 48px;
      text-align: center;
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 12px;
      color: #ffffff;
      background: var(--blue);
    }}
    .node-meta {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 500;
    }}
    .content {{
      margin: 8px 0 10px 56px;
      color: var(--muted);
      font-size: 13px;
    }}
    img {{
      display: block;
      width: 100%;
      min-width: 720px;
      height: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
    }}
    code {{
      background: #eef2f7;
      border-radius: 4px;
      padding: 2px 5px;
    }}
    @media (max-width: 980px) {{
      header, main {{ padding-left: 18px; padding-right: 18px; }}
      .stats, .grid, .pipeline, .algorithm, .api-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>DOCX 结构提取可视化报告</h1>
    <p class="subtitle">输入文件：{filename}</p>
  </header>
  <main>
    <section class="grid">
      <div class="panel">
        <h2>树形结果</h2>
        {tree_markup}
      </div>
      <div class="panel">
        <h2>SVG 结构图</h2>
        <img src="tree.svg" alt="DOCX 文档树结构图">
      </div>
    </section>
  </main>
</body>
</html>
"""


def _render_svg(root: NodeDict) -> str:
    """@brief 将文档树渲染为可插入 PPT 的 SVG 图。"""
    positioned = _position_nodes(root)
    width = max((node.x + 430 for node in positioned), default=960)
    height = max((node.y + 90 for node in positioned), default=540)
    by_index = {node.index: node for node in positioned}

    edge_markup = []
    node_markup = []
    for node in positioned:
        if node.parent_index is not None:
            parent = by_index[node.parent_index]
            start_x = parent.x + 360
            start_y = parent.y + 31
            end_x = node.x
            end_y = node.y + 31
            mid_x = (start_x + end_x) // 2
            edge_markup.append(
                f'<path d="M {start_x} {start_y} C {mid_x} {start_y}, {mid_x} {end_y}, '
                f'{end_x} {end_y}" fill="none" stroke="#94a3b8" stroke-width="2"/>'
            )

        fill, stroke = NODE_COLORS.get(node.level, ("#f3e8ff", "#7e22ce"))
        title_lines = _wrap_label(node.title, 24, 2)
        reason = node.detect_reason or "root"
        meta = _svg_text(f"L{node.level} | {reason} | 段落 {node.paragraph_count}", 28)
        title_spans = []
        for line_index, line in enumerate(title_lines):
            y = node.y + 24 + line_index * 17
            title_spans.append(
                f'<text x="{node.x + 18}" y="{y}" font-size="14" font-weight="700" '
                f'fill="#172033">{_svg_text(line, 28)}</text>'
            )
        node_markup.append(
            f'<rect x="{node.x}" y="{node.y}" width="360" height="62" rx="8" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
            + "".join(title_spans)
            + f'<text x="{node.x + 18}" y="{node.y + 52}" font-size="11" '
            f'fill="#475569">{meta}</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
  width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="32" y="36" font-size="24" font-weight="800" fill="#172033">DOCX 文档树结构图</text>
  {"".join(edge_markup)}
  {"".join(node_markup)}
</svg>
"""


def _position_nodes(root: NodeDict) -> list[PositionedNode]:
    """@brief 按先序遍历为 SVG 中的节点分配坐标。"""
    positioned: list[PositionedNode] = []

    def visit(node: NodeDict, depth: int, parent_index: int | None) -> None:
        index = len(positioned)
        paragraph_count, table_count = _direct_content_counts(node)
        positioned.append(
            PositionedNode(
                index=index,
                parent_index=parent_index,
                title=str(node.get("title", "")),
                level=int(node.get("level") or 0),
                depth=depth,
                x=32 + depth * 150,
                y=86 + index * 82,
                style_id=node.get("style_id"),
                style_name=node.get("style_name"),
                detect_reason=node.get("detect_reason"),
                paragraph_count=paragraph_count,
                table_count=table_count,
            )
        )
        for child in node.get("children", []):
            visit(child, depth + 1, index)

    visit(root, 0, None)
    return positioned


def _render_tree_details(node: NodeDict) -> str:
    """@brief 生成 HTML details 树。"""
    title = escape(str(node.get("title", "")))
    level = int(node.get("level") or 0)
    style_id = node.get("style_id") or "-"
    style_name = node.get("style_name") or "-"
    detect_reason = node.get("detect_reason") or "-"
    paragraph_count, table_count = _direct_content_counts(node)
    children = node.get("children", [])
    child_markup = "".join(_render_tree_details(child) for child in children)
    open_attr = " open" if level <= 2 else ""
    content = (
        f'<div class="content">样式 ID：{escape(str(style_id))}；样式名：'
        f'{escape(str(style_name))}；识别依据：{escape(str(detect_reason))}；'
        f"直属段落：{paragraph_count}；直属表格：{table_count}</div>"
    )
    return (
        f"<details{open_attr}>"
        f'<summary><span class="level">L{level}</span><span>{title}</span>'
        f'<span class="node-meta">{len(children)} 个子节点</span></summary>'
        f"{content}{child_markup}</details>"
    )


def _tree_stats(node: NodeDict) -> dict[str, int]:
    """@brief 统计整棵树中的层级、段落和表格数量。"""
    paragraphs, tables = _direct_content_counts(node)
    max_level = int(node.get("level") or 0)
    for child in node.get("children", []):
        child_stats = _tree_stats(child)
        paragraphs += child_stats["paragraphs"]
        tables += child_stats["tables"]
        max_level = max(max_level, child_stats["max_level"])
    return {"paragraphs": paragraphs, "tables": tables, "max_level": max_level}


def _direct_content_counts(node: NodeDict) -> tuple[int, int]:
    """@brief 统计当前节点直属内容中的段落和表格数量。"""
    paragraphs = 0
    tables = 0
    for item in node.get("content", []):
        item_type = item.get("type")
        if item_type == "paragraph":
            paragraphs += 1
        elif item_type == "table":
            tables += 1
    return paragraphs, tables


def _wrap_label(value: str, width: int, max_lines: int) -> list[str]:
    """@brief 将 SVG 节点标题拆成有限行数。"""
    lines = textwrap.wrap(value, width=width, max_lines=max_lines, placeholder="...")
    return lines or [""]


def _svg_text(value: str, limit: int) -> str:
    """@brief 截断并转义 SVG 文本。"""
    short = value if len(value) <= limit else value[: limit - 3] + "..."
    return escape(short, quote=True)


if __name__ == "__main__":
    main()
