"""DOCX 结构提取与样式替换包。"""

from docx_style_tree.extractor import analyze_docx
from docx_style_tree.style_replacer import replace_styles

__all__ = ["analyze_docx", "replace_styles"]
