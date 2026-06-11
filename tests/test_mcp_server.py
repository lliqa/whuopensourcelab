from __future__ import annotations

import unittest

from mcp_server import analyze_docx_file, get_parser_description


class McpServerTest(unittest.TestCase):
    def test_parser_description_exposes_pipeline(self) -> None:
        description = get_parser_description()

        self.assertEqual(description["name"], "ooxml_structure_tree")
        self.assertGreaterEqual(len(description["pipeline"]), 5)

    def test_analyze_docx_file_reuses_core_parser(self) -> None:
        result = analyze_docx_file(
            "tests/fixtures/geodesy_navigation_remote_sensing_thesis_template.docx"
        )

        self.assertEqual(result["format"], "docx")
        self.assertGreater(result["node_count"], 1)


if __name__ == "__main__":
    unittest.main()
