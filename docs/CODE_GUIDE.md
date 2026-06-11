# 代码导读

本文档面向课程报告、答辩和后续维护，说明当前代码如何组织、每个模块承担什么职责，以及从哪里开始理解系统。

## 阅读顺序

建议按以下顺序阅读代码：

1. `README.md`：了解项目做什么。
2. `app/main.py`：了解对外 API 如何封装。
3. `frontend/src/App.jsx`：了解现场演示页面如何调用 API。
4. `mcp_server.py`：了解解析能力如何包装成 MCP 工具。
5. `docx_style_tree/extractor.py`：理解文档树如何生成。
6. `docx_style_tree/ooxml.py`：理解 OOXML 辅助函数和块遍历。
7. `docx_style_tree/style_replacer.py`：理解样式替换如何保持 DOCX 包完整。
8. `tests/`：查看复杂 DOCX、真实论文模板和 API 校验用例。
9. `scripts/render_extraction_report.py`：查看可视化报告如何生成。

## 代码结构

```text
app/
└── main.py                       # FastAPI 服务入口

frontend/
└── src/App.jsx                   # React 单页演示

docx_style_tree/
├── __init__.py                   # 对外导出核心函数
├── errors.py                     # 领域异常
├── extractor.py                  # 文档结构提取
├── models.py                     # 文档树节点模型
├── ooxml.py                      # OOXML 命名空间、段落文本、块遍历
├── package.py                    # DOCX 包读取与 XML 解析
├── pipeline.py                   # 解析流程说明
└── style_replacer.py             # 结构样式替换

scripts/
├── download_fixtures.py          # 下载外部复杂 DOCX fixtures
└── render_extraction_report.py   # 生成 HTML/SVG/JSON 报告

tests/
├── test_api_validation.py        # API 上传与错误校验
├── test_cli.py                   # CLI 行为
├── test_docx_processing.py       # 核心解析与样式替换
├── test_external_fixtures.py     # 外部复杂 DOCX
├── test_local_thesis_template.py # 真实论文模板
└── test_thesis_docx_processing.py# 合成论文模板

mcp_server.py                     # MCP 工具入口
```

## 核心公共 API

包入口位于 `docx_style_tree/__init__.py`。

```python
from docx_style_tree import analyze_docx, describe_processing_pipeline, replace_styles
```

`analyze_docx(source)`：

- 输入：路径、bytes 或二进制文件对象。
- 输出：包含 `api_version`、`algorithm`、`metadata` 和 `tree` 的字典。
- 主要用于 API、CLI、报告生成和测试。

`replace_styles(source, style_map)`：

- 输入：DOCX 和结构角色到目标样式的映射。
- 输出：新的 DOCX bytes。
- 只修改必要 XML 部件，其他包部件尽量原样保留。

`describe_processing_pipeline()`：

- 输出：解析器名称、摘要和流程步骤。
- 主要用于 capabilities、React Demo、MCP 工具和 README 说明。

## 文档结构提取

主要文件：`docx_style_tree/extractor.py`

关键步骤：

```text
read_source
  -> ZipFile
  -> read_required_part("word/document.xml")
  -> read_style_names
  -> read_style_outline_levels
  -> parse_xml_part
  -> _build_tree
```

`_build_tree` 使用栈构建层级树：

```text
遇到标题 level=N：
  弹出所有 level >= N 的栈顶节点
  将新标题挂到当前栈顶
  新标题入栈

遇到普通段落或表格：
  挂到当前栈顶节点的 content
```

标题识别由 `detect_heading` 完成，它返回：

```text
level         标题层级
reason        识别依据
```

当前识别依据：

```text
paragraph_outline
style_outline
style_id
style_name
title_style
```

## OOXML 块遍历

主要文件：`docx_style_tree/ooxml.py`

`iter_body_blocks` 负责按正文顺序产出段落和表格。真实 DOCX 中，段落不一定是 `w:body` 的直接子节点，可能藏在：

```text
w:sdt
w:sdtContent
w:ins
w:customXml
w:smartTag
```

因此块遍历逻辑集中在一个地方，后续要支持新的透明容器，只需要扩展 `TRANSPARENT_BLOCK_CONTAINERS`。

需要特别处理 TOC：

- TOC 目录域保留在 DOCX 中。
- TOC 内容不参与文档树建章。
- 避免目录条目被误识别为正文标题。

## 样式替换

主要文件：`docx_style_tree/style_replacer.py`

设计目标：

- 复用与结构提取相同的 OOXML 块遍历。
- 根据结构角色选择目标样式。
- 如果目标样式不存在，可以追加最小样式定义。
- 重写 `word/document.xml` 和必要的 `word/styles.xml`。
- 保留图片、嵌入对象、页眉页脚、脚注、批注等其他部件。

结构角色映射：

```text
title
heading_1
heading_2
...
heading_6
normal
```

默认配置位于：

```text
config/predefined_styles.json
```

## FastAPI 服务

主要文件：`app/main.py`

对外接口：

```text
GET  /health
GET  /api/v1/capabilities
GET  /api/v1/demo/sample
POST /api/v1/analyze
POST /api/v1/styles/apply
POST /api/tree              # 兼容旧接口
POST /api/style             # 兼容旧接口
```

上传校验包括：

- 文件扩展名必须是 `.docx`。
- 上传体积限制。
- 解压后总体积限制。
- ZIP 成员路径不能是绝对路径或包含 `..`。
- 必须包含 `word/document.xml`。

## React 演示前端

主要文件：`frontend/src/App.jsx`

页面职责：

- 加载 `/api/v1/demo/sample`，展示仓库内置论文模板解析结果。
- 上传 `.docx` 文件到 `/api/v1/analyze`。
- 展示节点数、标题数、最大层级、段落和表格统计。
- 展示结构树和解析流程。

运行：

```bash
make demo-api
make frontend-install
make demo-ui
```

构建静态页面：

```bash
make frontend-build
```

构建后 FastAPI 会自动把 `frontend/dist` 挂载到 `/demo`。

## MCP 工具入口

主要文件：`mcp_server.py`

工具列表：

```text
describe_docx_parser
analyze_docx_path
apply_docx_styles_path
```

运行：

```bash
uv sync --extra mcp
uv run --extra mcp docx-style-tree-mcp
```

## 报告生成

主要文件：`scripts/render_extraction_report.py`

运行：

```bash
make report
```

输出：

```text
outputs/extraction-report/
├── index.html
├── tree.svg
└── tree.json
```

报告只展示解析结果，不放算法说明或演示讲稿。算法解释应放在 README 和架构文档中。

## 测试策略

当前测试覆盖：

- 基础 DOCX 解析。
- 标题样式和 `outlineLvl` 识别。
- 正文中类似标题的内容不会被误判为结构标题。
- 表格文本提取。
- 内容控件、TOC、修订和复杂包部件。
- 样式替换和样式创建。
- FastAPI 上传校验。
- CLI 行为。
- 真实论文模板 fixture。
- 外部复杂 DOCX fixtures。

运行完整检查：

```bash
make check
```

当前本地结果：

```text
以 `make check` 输出为准。
```

## 后续代码扩展点

| 需求 | 建议位置 |
|---|---|
| 模板与论文比较 | 新增 `docx_style_tree/comparator.py`。 |
| 样式画像提取 | 扩展 `package.py` 或新增 `profile.py`。 |
| API schema | 在 `app/main.py` 或新 `app/schemas.py` 中增加 Pydantic 模型。 |
| 诊断报告页面 | 扩展 `scripts/render_extraction_report.py`。 |
| 批量比较 CLI | 扩展 `cli.py`。 |

代码扩展应优先复用核心包，避免把业务逻辑散落到 API、CLI 或报告脚本中。
