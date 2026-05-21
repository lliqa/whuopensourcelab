# DOCX 文档结构提取与样式替换实验

作者：lc, syg  
课程：武汉大学开源软件与技术课程 2026  
许可证：MIT License

## 项目简介

本项目使用 Python + FastAPI 实现对 `.docx` 文档的自动处理：

- 提取段落、标题、表格等主要结构信息。
- 生成层级化文档树 JSON。
- 按预定义 style 配置统一替换文档结构样式。
- 提供 Web API 与命令行两种使用方式。

项目不依赖 Microsoft Word 或 LibreOffice，核心 `.docx` 处理基于 Office Open XML 标准和 Python 标准库完成。

## 目录结构

```text
.
├── app/                         # FastAPI 应用入口
├── config/                      # 预定义样式配置
├── docs/                        # 实验说明与全局完整文档
├── docx_style_tree/             # 核心解析与样式替换模块
├── tests/                       # 单元测试
├── cli.py                       # 命令行工具
├── requirements.txt             # 运行依赖
├── pyproject.toml               # 项目元数据
├── LICENSE                      # 开源许可证
└── todo.md                      # 实验要求
```

## 环境准备

建议使用 Linux 或 WSL 环境，Python 版本由 `uv` 管理。本仓库通过 `.python-version` 固定为 Python 3.11。

```bash
uv python install 3.11
uv sync
```

## 启动 FastAPI 服务

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

启动后访问：

- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health

## API 使用

### 提取文档树

```bash
curl -X POST "http://127.0.0.1:8000/api/tree" \
  -F "file=@example.docx"
```

### 替换文档样式

```bash
curl -X POST "http://127.0.0.1:8000/api/style" \
  -F "file=@example.docx" \
  --output styled.docx
```

也可以提交自定义样式映射：

```bash
curl -X POST "http://127.0.0.1:8000/api/style" \
  -F "file=@example.docx" \
  -F 'style_map={"heading_1":"Heading 1","heading_2":"Heading 2","normal":"Normal"}' \
  --output styled.docx
```

## 命令行使用

提取文档树：

```bash
uv run python cli.py analyze example.docx -o tree.json
```

替换文档样式：

```bash
uv run python cli.py style example.docx -o styled.docx
```

指定样式配置：

```bash
uv run python cli.py style example.docx -o styled.docx --styles config/predefined_styles.json
```

## 测试

```bash
uv run python -m unittest discover -s tests