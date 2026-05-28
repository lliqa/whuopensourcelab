from __future__ import annotations

import os
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

from docx_style_tree import analyze_docx, replace_styles
from docx_style_tree.ooxml import NS, attr, paragraph_text

REPO_THESIS_TEMPLATE_PATH = (
    Path(__file__).parent / "fixtures" / "geodesy_navigation_remote_sensing_thesis_template.docx"
)
LOCAL_THESIS_TEMPLATE_PATH = Path(
    os.environ.get(
        "THESIS_TEMPLATE_DOCX",
        str(REPO_THESIS_TEMPLATE_PATH),
    )
)


@unittest.skipUnless(
    LOCAL_THESIS_TEMPLATE_PATH.exists(),
    "thesis template fixture is unavailable; set THESIS_TEMPLATE_DOCX to run this test",
)
class LocalThesisTemplateTest(unittest.TestCase):
    def test_analyze_local_thesis_template_tree(self) -> None:
        result = analyze_docx(LOCAL_THESIS_TEMPLATE_PATH)

        root = result["tree"]
        self.assertEqual(result["node_count"], 12)
        self.assertEqual(
            [child["title"] for child in root["children"]],
            [
                "大地测量与导航、摄影测量与遥感研究论文",
                "A Review of Dense Stereo Image Matching Methods Based on Deep Learning",
            ],
        )

        english_title = root["children"][1]
        self.assertEqual(
            [child["title"] for child in english_title["children"]],
            [
                "（本刊不标注“引言”，不要标注更不要编号）",
                "1  有突出特色和名称的研究方法",
                "2  性能评估",
                "3  结 语",
                "参考文献",
            ],
        )

        method = english_title["children"][1]
        self.assertEqual(
            [child["title"] for child in method["children"]],
            ["1.1  代价函数", "1.2 多种导航增强观测数据仿真算法"],
        )
        self.assertEqual(method["children"][1]["children"][0]["level"], 4)

    def test_style_replacement_preserves_local_thesis_complex_parts(self) -> None:
        original_parts = _read_parts(LOCAL_THESIS_TEMPLATE_PATH)

        output = replace_styles(
            LOCAL_THESIS_TEMPLATE_PATH,
            {
                "heading_1": "Template Heading 1",
                "heading_2": "Template Heading 2",
                "heading_3": "Template Heading 3",
                "normal": "Template Body",
            },
        )
        updated_parts = _read_parts(output)

        for part_name in [
            "word/header1.xml",
            "word/footer1.xml",
            "word/footnotes.xml",
            "word/endnotes.xml",
            "word/embeddings/oleObject1.bin",
            "word/media/image1.png",
        ]:
            self.assertIn(part_name, updated_parts)
            self.assertEqual(updated_parts[part_name], original_parts[part_name])

        document_root = ET.fromstring(updated_parts["word/document.xml"])
        styles_by_text = _paragraph_styles_by_text(document_root)
        self.assertEqual(
            styles_by_text["大地测量与导航、摄影测量与遥感研究论文"],
            "TemplateHeading1",
        )
        self.assertEqual(styles_by_text["1  有突出特色和名称的研究方法"], "TemplateHeading2")
        self.assertEqual(styles_by_text["1.1  代价函数"], "TemplateHeading3")


def _read_parts(source: Path | bytes) -> dict[str, bytes]:
    package_source = BytesIO(source) if isinstance(source, bytes) else source
    with zipfile.ZipFile(package_source) as package:
        return {info.filename: package.read(info.filename) for info in package.infolist()}


def _paragraph_styles_by_text(document_root: ET.Element) -> dict[str, str | None]:
    styles: dict[str, str | None] = {}
    for paragraph in document_root.findall(".//w:p", NS):
        text = paragraph_text(paragraph)
        if not text:
            continue
        style = paragraph.find("./w:pPr/w:pStyle", NS)
        styles[text] = attr(style, "val") if style is not None else None
    return styles


if __name__ == "__main__":
    unittest.main()
