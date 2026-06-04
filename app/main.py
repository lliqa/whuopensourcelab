"""DOCX 文档树提取与样式替换的 FastAPI 服务。

@author lliqa
@course 武汉大学开源软件与技术课程 2026
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
    """@brief 返回服务健康状态。"""
    return {"status": "ok"}


@app.get("/api/v1/capabilities", tags=["v1"])
def service_capabilities() -> dict[str, Any]:
    """@brief 返回服务对外暴露的能力描述。"""
    return {
        "service": "docx-style-tree",
        "api_version": "1.0",
        "features": [
            "extract_document_tree",
            "apply_structural_styles",
            "heading_detection_diagnostics",
            "nested_ooxml_block_traversal",
        ],
        "limits": {
            "max_upload_bytes": MAX_UPLOAD_BYTES,
            "max_uncompressed_bytes": MAX_UNCOMPRESSED_BYTES,
        },
        "algorithm": {
            "name": "ooxml_structure_tree",
            "uses_text_matching": False,
            "summary": "解析 document.xml 与 styles.xml，依据样式和 outlineLvl 构建类 AST 文档树。",
        },
    }


@app.post("/api/v1/analyze", tags=["v1"])
async def analyze_document_v1(file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    """@brief v1 对外 API：从上传的 DOCX 文件提取结构树。"""
    return await _analyze_upload(file)


@app.post("/api/v1/styles/apply", tags=["v1"])
async def apply_styles_v1(
    file: Annotated[UploadFile, File()],
    style_map: Annotated[str | None, Form()] = None,
) -> StreamingResponse:
    """@brief v1 对外 API：按结构角色替换 DOCX 样式。"""
    return await _replace_style_upload(file, style_map)


@app.post("/api/tree")
async def extract_tree(file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    """@brief 从上传的 DOCX 文件中提取文档树信息。"""
    return await _analyze_upload(file)


@app.post("/api/style")
async def replace_document_style(
    file: Annotated[UploadFile, File()],
    style_map: Annotated[str | None, Form()] = None,
) -> StreamingResponse:
    """@brief 替换文档结构样式并返回更新后的 DOCX。"""
    return await _replace_style_upload(file, style_map)


async def _analyze_upload(file: UploadFile) -> dict[str, Any]:
    """@brief 读取上传文件并调用文档结构提取服务。"""
    docx_bytes = await _read_docx_upload(file)
    try:
        return analyze_docx(docx_bytes)
    except InvalidDocxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _replace_style_upload(
    file: UploadFile,
    style_map: str | None = None,
) -> StreamingResponse:
    """@brief 读取上传文件并调用文档样式替换服务。"""
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
    """@brief 校验上传文件名并读取请求体。"""
    if file.filename and not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")
    data = await _read_limited_upload(file)
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    _validate_docx_archive(data)
    return data


async def _read_limited_upload(file: UploadFile) -> bytes:
    """@brief 在压缩体积限制内读取上传内容。"""
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
    """@brief 拒绝无效 DOCX 压缩包和解压后过大的文件。"""
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
    """@brief 拒绝不安全的压缩包成员路径。"""
    path = PurePosixPath(filename)
    if path.is_absolute() or ".." in path.parts:
        raise HTTPException(status_code=400, detail="Invalid DOCX file.")


def _parse_style_map(style_map: str | None) -> Mapping[str, object]:
    """@brief 将可选的 style_map 表单数据解析为映射。"""
    if style_map is None:
        return load_style_map()
    data = json.loads(style_map)
    if not isinstance(data, dict):
        raise InvalidStyleMapError("style_map must be a JSON object.")
    return cast(dict[str, object], data)


def _styled_filename(filename: str | None) -> str:
    """@brief 为样式替换输出构造下载文件名。"""
    if not filename:
        return "styled.docx"
    if filename.lower().endswith(".docx"):
        return f"{filename[:-5]}_styled.docx"
    return f"{filename}_styled.docx"
