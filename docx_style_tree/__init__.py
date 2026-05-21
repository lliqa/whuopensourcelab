"""DOCX structure extraction and style replacement package."""

from docx_style_tree.extractor import analyze_docx
from docx_style_tree.style_replacer import replace_styles

__all__ = ["analyze_docx", "replace_styles"]
