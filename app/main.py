"""FastAPI service for DOCX tree extraction and style replacement.

@author lliqa
@course Wuhan University Open Source Software and Technology 2026
"""

from __future__ import annotations

import json
import zipfile
from io import BytesIO

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from docx_style_tree import analyze_docx, replace_styles
from docx_style_tree.style_replacer import load_style_map

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
async def extract_tree(file: UploadFile = File(...)) -> dict:
    """@brief Extract document tree information from an uploaded DOCX file."""
    docx_bytes = await _read_docx_upload(file)
    try:
        return analyze_docx(docx_bytes)
    except (KeyError, zipfile.BadZipFile) as exc:
        raise HTTPException(status_code=400, detail="Invalid DOCX file.") from exc


@app.post("/api/style")
async def replace_document_style(
    file: UploadFile = File(...),
    style_map: str | None = Form(default=None),
) -> StreamingResponse:
    """@brief Replace structural styles and return the updated DOCX."""
    docx_bytes = await _read_docx_upload(file)
    try:
        mapping = json.loads(style_map) if style_map else load_style_map("config/predefined_styles.json")
        output = replace_styles(docx_bytes, mapping)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="style_map must be valid JSON.") from exc
    except (KeyError, zipfile.BadZipFile) as exc:
        raise HTTPException(status_code=400, detail="Invalid DOCX file.") from exc

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
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    return data


def _styled_filename(filename: str | None) -> str:
    """@brief Build a download filename for styled output."""
    if not filename:
        return "styled.docx"
    if filename.lower().endswith(".docx"):
        return f"{filename[:-5]}_styled.docx"
    return f"{filename}_styled.docx"
