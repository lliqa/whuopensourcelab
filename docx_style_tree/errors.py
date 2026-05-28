"""DOCX 处理相关的领域异常。

@author lliqa
@course 武汉大学开源软件与技术课程 2026
"""

from __future__ import annotations


class DocxStyleTreeError(Exception):
    """@brief DOCX 样式树处理中可预期失败的基础异常。"""


class InvalidDocxError(DocxStyleTreeError):
    """@brief 输入压缩包不是有效 DOCX 文档时抛出。"""


class InvalidStyleMapError(DocxStyleTreeError, ValueError):
    """@brief 样式映射缺失或格式错误时抛出。"""
