from __future__ import annotations

import os
import unittest
import zipfile
from io import BytesIO

from fastapi import HTTPException, UploadFile
from test_docx_processing import _make_docx

import app.main as app_main
from app.main import (
    _parse_style_map,
    _read_docx_upload,
    _validate_docx_archive,
    analyze_document_v1,
    apply_styles_v1,
    extract_tree,
    replace_document_style,
    service_capabilities,
)
from docx_style_tree.errors import InvalidStyleMapError


class ApiValidationTest(unittest.IsolatedAsyncioTestCase):
    async def test_read_upload_rejects_non_docx_extension(self) -> None:
        file = UploadFile(filename="input.txt", file=BytesIO(b"not a docx"))

        with self.assertRaises(HTTPException) as context:
            await _read_docx_upload(file)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.detail, "Only .docx files are supported.")

    async def test_read_upload_rejects_invalid_zip(self) -> None:
        file = UploadFile(filename="input.docx", file=BytesIO(b"not a zip"))

        with self.assertRaises(HTTPException) as context:
            await _read_docx_upload(file)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.detail, "Invalid DOCX file.")

    async def test_read_upload_rejects_empty_file(self) -> None:
        file = UploadFile(filename="input.docx", file=BytesIO(b""))

        with self.assertRaises(HTTPException) as context:
            await _read_docx_upload(file)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.detail, "Uploaded file is empty.")

    async def test_extract_tree_endpoint_returns_tree(self) -> None:
        file = UploadFile(filename="input.docx", file=BytesIO(_make_docx()))

        result = await extract_tree(file)

        self.assertEqual(result["node_count"], 3)

    async def test_analyze_v1_endpoint_returns_api_metadata(self) -> None:
        file = UploadFile(filename="input.docx", file=BytesIO(_make_docx()))

        result = await analyze_document_v1(file)

        self.assertEqual(result["api_version"], "1.0")
        self.assertEqual(result["algorithm"]["name"], "ooxml_structure_tree")
        self.assertIn("metadata", result)

    async def test_replace_style_endpoint_returns_docx_response(self) -> None:
        file = UploadFile(filename="input.docx", file=BytesIO(_make_docx()))

        response = await replace_document_style(file)

        self.assertEqual(
            response.media_type,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertIn("input_styled.docx", response.headers["content-disposition"])

    async def test_apply_styles_v1_endpoint_returns_docx_response(self) -> None:
        file = UploadFile(filename="input.docx", file=BytesIO(_make_docx()))

        response = await apply_styles_v1(file)

        self.assertEqual(response.status_code, 200)

    def test_service_capabilities_exposes_public_contract(self) -> None:
        result = service_capabilities()

        self.assertEqual(result["api_version"], "1.0")
        self.assertFalse(result["algorithm"]["uses_text_matching"])
        self.assertIn("nested_ooxml_block_traversal", result["features"])

    async def test_replace_style_endpoint_rejects_invalid_json(self) -> None:
        file = UploadFile(filename="input.docx", file=BytesIO(_make_docx()))

        with self.assertRaises(HTTPException) as context:
            await replace_document_style(file, "{")

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.detail, "style_map must be valid JSON.")

    async def test_replace_style_endpoint_accepts_new_target_style(self) -> None:
        file = UploadFile(filename="input.docx", file=BytesIO(_make_docx()))

        response = await replace_document_style(file, '{"heading_1":"Missing Heading"}')

        self.assertEqual(response.status_code, 200)

    def test_parse_style_map_rejects_non_object_json(self) -> None:
        with self.assertRaises(InvalidStyleMapError):
            _parse_style_map("[]")

    def test_default_style_map_is_independent_of_current_directory(self) -> None:
        previous_cwd = os.getcwd()
        try:
            os.chdir("/tmp")
            mapping = _parse_style_map(None)
        finally:
            os.chdir(previous_cwd)

        self.assertEqual(mapping["heading_1"], "Heading1")

    def test_validate_archive_rejects_missing_document_part(self) -> None:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
            package.writestr("[Content_Types].xml", "<Types/>")

        with self.assertRaises(HTTPException) as context:
            _validate_docx_archive(buffer.getvalue())

        self.assertEqual(context.exception.status_code, 400)

    def test_validate_archive_rejects_unsafe_member_name(self) -> None:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
            package.writestr("word/document.xml", "<w:document/>")
            package.writestr("../bad", "bad")

        with self.assertRaises(HTTPException) as context:
            _validate_docx_archive(buffer.getvalue())

        self.assertEqual(context.exception.status_code, 400)

    def test_validate_archive_rejects_large_expanded_size(self) -> None:
        previous_limit = app_main.MAX_UNCOMPRESSED_BYTES
        app_main.MAX_UNCOMPRESSED_BYTES = 1
        try:
            with self.assertRaises(HTTPException) as context:
                _validate_docx_archive(_make_docx())
        finally:
            app_main.MAX_UNCOMPRESSED_BYTES = previous_limit

        self.assertEqual(context.exception.status_code, 413)


if __name__ == "__main__":
    unittest.main()
