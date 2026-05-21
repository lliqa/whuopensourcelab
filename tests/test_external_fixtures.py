from __future__ import annotations

import hashlib
import json
import os
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, ClassVar
from xml.etree import ElementTree as ET

from docx_style_tree import analyze_docx, replace_styles
from docx_style_tree.ooxml import local_name

MANIFEST_PATH = Path(__file__).parent / "fixtures" / "docx_manifest.json"
FIXTURE_DIR = Path(os.environ.get("DOCX_FIXTURE_DIR", ".fixtures/docx"))


class ExternalDocxFixtureTest(unittest.TestCase):
    fixtures: ClassVar[list[dict[str, Any]]] = []

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = _load_manifest()

    def setUp(self) -> None:
        missing = [
            fixture["name"] for fixture in self.fixtures if not _fixture_path(fixture).exists()
        ]
        if missing:
            self.skipTest("external DOCX fixtures are not downloaded; run `make fixtures`")

    def test_downloaded_fixtures_match_manifest_checksums(self) -> None:
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture["name"]):
                self.assertEqual(_sha256(_fixture_path(fixture)), fixture["sha256"])

    def test_complex_fixtures_match_tree_expectations(self) -> None:
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture["name"]):
                result = analyze_docx(_fixture_path(fixture))
                expected = fixture["expected"]

                self.assertEqual(result["node_count"], expected["node_count"])
                if "top_titles" in expected:
                    top_titles = [child["title"] for child in result["tree"]["children"]]
                    self.assertEqual(
                        top_titles[: len(expected["top_titles"])], expected["top_titles"]
                    )
                for title, expected_children in expected.get("child_titles", {}).items():
                    node = _find_node(result["tree"], title)
                    if node is None:
                        self.fail(f"missing expected node: {title}")
                    self.assertEqual(
                        [child["title"] for child in node["children"]],
                        expected_children,
                    )

    def test_style_replacement_preserves_complex_package_parts(self) -> None:
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture["name"]):
                path = _fixture_path(fixture)
                original_parts = _read_parts(path)
                output = replace_styles(path)
                updated_parts = _read_parts(output)

                self.assertIn("word/document.xml", updated_parts)
                ET.fromstring(updated_parts["word/document.xml"])
                if "word/styles.xml" in updated_parts:
                    ET.fromstring(updated_parts["word/styles.xml"])

                for part_name in fixture["expected"].get("required_parts", []):
                    self.assertIn(part_name, updated_parts)
                    self.assertEqual(updated_parts[part_name], original_parts[part_name])

                updated_tags = _document_tags(updated_parts["word/document.xml"])
                for tag_name in fixture["expected"].get("required_tags", []):
                    self.assertIn(tag_name, updated_tags)


def _load_manifest() -> list[dict[str, Any]]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return data["fixtures"]


def _fixture_path(fixture: dict[str, Any]) -> Path:
    return FIXTURE_DIR / fixture["name"]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_parts(source: Path | bytes) -> dict[str, bytes]:
    package_source = BytesIO(source) if isinstance(source, bytes) else source
    with zipfile.ZipFile(package_source) as package:
        return {info.filename: package.read(info.filename) for info in package.infolist()}


def _document_tags(document_xml: bytes) -> set[str]:
    root = ET.fromstring(document_xml)
    return {local_name(element.tag) for element in root.iter()}


def _find_node(node: dict[str, Any], title: str) -> dict[str, Any] | None:
    if node["title"] == title:
        return node
    for child in node["children"]:
        result = _find_node(child, title)
        if result is not None:
            return result
    return None


if __name__ == "__main__":
    unittest.main()
