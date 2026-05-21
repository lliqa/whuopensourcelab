from __future__ import annotations

import json
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from test_docx_processing import _make_docx

import cli


class CliTest(unittest.TestCase):
    def test_analyze_command_writes_json(self) -> None:
        with TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.docx"
            output_path = Path(directory) / "tree.json"
            input_path.write_bytes(_make_docx())

            with patch("sys.argv", ["cli.py", "analyze", str(input_path), "-o", str(output_path)]):
                cli.main()

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["node_count"], 3)

    def test_style_command_writes_docx(self) -> None:
        with TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.docx"
            output_path = Path(directory) / "styled.docx"
            input_path.write_bytes(_make_docx())

            with patch("sys.argv", ["cli.py", "style", str(input_path), "-o", str(output_path)]):
                cli.main()

            self.assertEqual(output_path.read_bytes()[:4], b"PK\x03\x04")

    def test_cli_reports_expected_failures_without_traceback(self) -> None:
        with (
            patch("sys.argv", ["cli.py", "analyze", "missing.docx"]),
            patch("sys.stderr", new_callable=StringIO),
            self.assertRaises(SystemExit) as context,
        ):
            cli.main()

        self.assertEqual(context.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
