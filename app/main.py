"""FastAPI service for DOCX tree extraction and style replacement.

@author lliqa
@course Wuhan University Open Source Software and Technology 2026
"""

from __future__ import annotations

import json
import zipfile
from collections.abc import Mapping
from io import BytesIO
from pathlib import PurePosixPath
from typing import Annotated, Any, cast

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from docx_style_tree import analyze_docx, replace_styles
from docx_style_tree.errors import InvalidDocxError, InvalidStyleMapError
from docx_style_tree.style_replacer import load_style_map

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
READ_CHUNK_BYTES = 1024 * 1024

app = FastAPI(
    title="DOCX 文档结构提取与样式替换实验",
    description="武汉大学开源软件与技术课程 2026 实验项目",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """@brief Return service health status."""
    return {"status": "ok"}


@app.post("/api/tree")
async def extract_tree(file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    """@brief Extract document tree information from an uploaded DOCX file."""
    docx_bytes = await _read_docx_upload(file)
    try:
        return analyze_docx(docx_bytes)
    except InvalidDocxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/style")
async def replace_document_style(
    file: Annotated[UploadFile, File()],
    style_map: Annotated[str | None, Form()] = None,
) -> StreamingResponse:
    """@brief Replace structural styles and return the updated DOCX."""
    docx_bytes = await _read_docx_upload(file)
    try:
        mapping = _parse_style_map(style_map)
        output = replace_styles(docx_bytes, mapping)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="style_map must be valid JSON.") from exc
    except InvalidStyleMapError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidDocxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filename = _styled_filename(file.filename)
    return StreamingResponse(
        BytesIO(output),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _read_docx_upload(file: UploadFile) -> bytes:
    """@brief Validate upload name and read request body."""
    if file.filename and not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")
    data = await _read_limited_upload(file)
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    _validate_docx_archive(data)
    return data


async def _read_limited_upload(file: UploadFile) -> bytes:
    """@brief Read an upload while enforcing a compressed size limit."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Uploaded file is too large.")
        chunks.append(chunk)
    return b"".join(chunks)


def _validate_docx_archive(data: bytes) -> None:
    """@brief Reject invalid DOCX archives and oversized expanded packages."""
    try:
        with zipfile.ZipFile(BytesIO(data)) as package:
            names = set(package.namelist())
            if "word/document.xml" not in names:
                raise HTTPException(status_code=400, detail="Invalid DOCX file.")

            total_uncompressed = 0
            for info in package.infolist():
                _validate_archive_member_name(info.filename)
                total_uncompressed += info.file_size
                if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                    raise HTTPException(status_code=413, detail="Uploaded DOCX expands too large.")
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Invalid DOCX file.") from exc


def _validate_archive_member_name(filename: str) -> None:
    """@brief Reject unsafe archive member names."""
    path = PurePosixPath(filename)
    if path.is_absolute() or ".." in path.parts:
        raise HTTPException(status_code=400, detail="Invalid DOCX file.")


def _parse_style_map(style_map: str | None) -> Mapping[str, object]:
    """@brief Parse optional style_map form data into a mapping."""
    if style_map is None:
        return load_style_map()
    data = json.loads(style_map)
    if not isinstance(data, dict):
        raise InvalidStyleMapError("style_map must be a JSON object.")
    return cast(dict[str, object], data)


def _styled_filename(filename: str | None) -> str:
    """@brief Build a download filename for styled output."""
    if not filename:
        return "styled.docx"
    if filename.lower().endswith(".docx"):
        return f"{filename[:-5]}_styled.docx"
    return f"{filename}_styled.docx"
