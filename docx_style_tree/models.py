"""Data models used by DOCX structure extraction.

@author lliqa
@course Wuhan University Open Source Software and Technology 2026
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentNode:
    """@brief A node in the extracted document tree."""

    title: str
    level: int
    style_id: str | None = None
    style_name: str | None = None
    content: list[dict[str, Any]] = field(default_factory=list)
    children: list[DocumentNode] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """@brief Convert the node and descendants to JSON-ready data."""
        return {
            "title": self.title,
            "level": self.level,
            "style_id": self.style_id,
            "style_name": self.style_name,
            "content": self.content,
            "children": [child.to_dict() for child in self.children],
        }
