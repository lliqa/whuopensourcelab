"""DOCX 结构提取使用的数据模型。

@author lliqa
@course 武汉大学开源软件与技术课程 2026
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentNode:
    """@brief 提取出的文档树节点。"""

    title: str
    level: int
    node_type: str = "heading"
    style_id: str | None = None
    style_name: str | None = None
    detect_reason: str | None = None
    block_index: int | None = None
    container_path: tuple[str, ...] = ()
    content: list[dict[str, Any]] = field(default_factory=list)
    children: list[DocumentNode] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """@brief 将当前节点及其子孙节点转换为可序列化 JSON 的数据。"""
        return {
            "title": self.title,
            "level": self.level,
            "node_type": self.node_type,
            "style_id": self.style_id,
            "style_name": self.style_name,
            "detect_reason": self.detect_reason,
            "block_index": self.block_index,
            "container_path": list(self.container_path),
            "content": self.content,
            "children": [child.to_dict() for child in self.children],
        }
