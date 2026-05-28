"""下载外部 DOCX fixtures 并校验 SHA256。

@author lliqa
@course 武汉大学开源软件与技术课程 2026
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path("tests/fixtures/docx_manifest.json")
DEFAULT_DESTINATION = Path(".fixtures/docx")


def main() -> None:
    """@brief 解析参数并下载 manifest 中的全部 fixtures。"""
    parser = argparse.ArgumentParser(description="Download DOCX fixtures with SHA256 checks.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args()

    manifest = _load_manifest(args.manifest)
    args.dest.mkdir(parents=True, exist_ok=True)

    for fixture in manifest["fixtures"]:
        path = args.dest / fixture["name"]
        expected_sha = fixture["sha256"]
        if path.exists() and _sha256(path) == expected_sha:
            print(f"ok {path}")
            continue

        _download(fixture["url"], path)
        actual_sha = _sha256(path)
        if actual_sha != expected_sha:
            path.unlink(missing_ok=True)
            raise SystemExit(
                f"checksum mismatch for {fixture['name']}: "
                f"expected {expected_sha}, got {actual_sha}"
            )
        print(f"downloaded {path}")


def _load_manifest(path: Path) -> dict[str, list[dict[str, Any]]]:
    """@brief 读取 fixture manifest 并执行最小校验。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("fixtures"), list):
        raise SystemExit("fixture manifest must contain a fixtures list")
    return data


def _download(url: str, path: Path) -> None:
    """@brief 通过临时文件下载单个 fixture。"""
    request = urllib.request.Request(url, headers={"User-Agent": "whuopensourcelab-fixtures"})
    with (
        urllib.request.urlopen(request, timeout=60) as response,
        tempfile.NamedTemporaryFile(delete=False, dir=path.parent) as temp_file,
    ):
        temp_path = Path(temp_file.name)
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            temp_file.write(chunk)
    temp_path.replace(path)


def _sha256(path: Path) -> str:
    """@brief 返回文件的 SHA256 摘要。"""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
