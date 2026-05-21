"""Command line interface for DOCX structure extraction and style replacement.

@author lliqa
@course Wuhan University Open Source Software and Technology 2026
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from docx_style_tree import analyze_docx, replace_styles
from docx_style_tree.style_replacer import load_style_map


def main() -> None:
    """@brief Parse arguments and execute the selected command."""
    parser = argparse.ArgumentParser(description="DOCX tree extraction and style replacement.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="extract a DOCX document tree")
    analyze_parser.add_argument("input", type=Path, help="input .docx file")
    analyze_parser.add_argument("-o", "--output", type=Path, help="output JSON file")

    style_parser = subparsers.add_parser("style", help="replace structural styles")
    style_parser.add_argument("input", type=Path, help="input .docx file")
    style_parser.add_argument("-o", "--output", type=Path, required=True, help="output .docx file")
    style_parser.add_argument("--styles", type=Path, help="style mapping JSON file")

    args = parser.parse_args()
    if args.command == "analyze":
        _analyze(args.input, args.output)
    elif args.command == "style":
        _style(args.input, args.output, args.styles)


def _analyze(input_path: Path, output_path: Path | None) -> None:
    """@brief Analyze a document and write JSON to file or stdout."""
    result = analyze_docx(input_path)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if output_path:
        output_path.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


def _style(input_path: Path, output_path: Path, style_path: Path | None) -> None:
    """@brief Apply predefined styles and write an updated DOCX file."""
    mapping = load_style_map(style_path)
    output_path.write_bytes(replace_styles(input_path, mapping))


if __name__ == "__main__":
    main()
