"""DOCX 结构提取与样式替换包。"""

from docx_style_tree.extractor import analyze_docx
from docx_style_tree.pipeline import describe_processing_pipeline
from docx_style_tree.style_replacer import replace_styles

__all__ = ["analyze_docx", "describe_processing_pipeline", "replace_styles"]
