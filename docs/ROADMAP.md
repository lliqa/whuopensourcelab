# 后续升级路线

本文档记录 `DOCX Style Tree` 后续可以如何迭代。规划参考成熟开源项目常见做法：先明确用户场景，再稳定 API 合约，随后补充示例、报告、测试和部署能力。所有升级都限制在 DOCX 结构解析、样式检查和论文格式一致性范围内，不扩展到与课程题目无关的写作、查重或语义评价。

## 产品方向

当前项目已经具备 DOCX 结构提取、样式替换、FastAPI 接口和可视化报告。下一步最有吸引力的方向是：

> 比较模板 DOCX 与实际论文 DOCX，判断论文格式是否与模板一致。

这会把项目从“解析工具”升级为“论文格式一致性检查服务”。它仍然围绕 DOCX 结构和样式，不偏离课程要求，同时更接近真实使用场景。

典型用户：

- 学生：提交前检查毕业论文、课程报告是否符合模板。
- 教师：快速检查学生文档结构和样式是否规范。
- 小组项目：合并多人文档后统一标题、正文和表格样式。
- 实验室或课程组：维护一套模板，自动检测文档偏差。

## 设计原则

参考成熟开源项目的迭代方式，后续优化遵循这些原则：

- **场景优先**：围绕“DOCX 模板一致性检查”和“样式规范化”设计功能。
- **API 稳定**：使用 `/api/v1` 维护对外接口，新增能力不破坏旧接口。
- **结果可解释**：每个判断都应说明依据，例如 `style_outline`、`paragraph_outline`、样式 ID 或样式名称。
- **报告可截图**：演示材料应能直接放进 README、PPT 或课程报告。
- **测试可复现**：复杂 DOCX、真实论文模板和外部 fixture 都应纳入自动化测试。
- **范围克制**：不做 PDF/OCR、查重、语法纠错、AI 写作和完整 Word 排版引擎。

## 里程碑 1：模板与论文一致性比较

目标：增加一个可以比较两份 DOCX 的核心能力。

建议 API：

```text
POST /api/v1/compare
```

请求：

```text
template: 模板 DOCX
document: 实际论文 DOCX
```

返回示例：

```json
{
  "api_version": "1.0",
  "verdict": "failed",
  "score": 82,
  "summary": {
    "structure": 90,
    "styles": 76,
    "layout": 85
  },
  "issues": [
    {
      "severity": "error",
      "location": "第二章 系统设计",
      "message": "二级标题样式与模板不一致",
      "expected": "Heading 2",
      "actual": "Normal"
    }
  ]
}
```

比较方式不应比较正文内容，而应比较“文档结构画像”。

模板画像：

```text
template.docx
  -> structure profile
  -> style profile
  -> layout profile
  -> required sections
```

论文画像：

```text
paper.docx
  -> structure profile
  -> style profile
  -> layout profile
  -> observed sections
```

比较维度：

| 维度 | 检查内容 |
|---|---|
| 标题结构 | 标题层级、标题跳级、必要章节是否存在。 |
| 样式一致性 | 标题、正文、题注等结构角色是否使用模板样式。 |
| 页面设置 | 纸张大小、页边距、页眉页脚和分节信息。 |
| 表格与题注 | 表格是否存在题注，题注样式是否一致。 |
| 包结构 | 图片、嵌入对象、脚注、批注等是否被正确保留。 |

第一版可以先实现标题结构和样式一致性；页面设置和题注检查作为后续增强。

## 里程碑 2：正式 API Schema

目标：让 API 文档更像可交付服务。

计划：

- 使用 Pydantic 定义响应模型。
- 为 `/api/v1/analyze`、`/api/v1/styles/apply`、`/api/v1/compare` 增加清晰的 OpenAPI schema。
- 在 `/docs` 中展示示例响应。
- 将错误响应统一为结构化格式。

建议模型：

```text
AnalyzeResponse
CompareResponse
DocumentNode
ContentBlock
TableBlock
HeadingDetection
FormatIssue
```

收益：

- FastAPI 自动生成的接口文档更清晰。
- 前端或其他系统更容易集成。
- 课程展示时能体现 API 抽象和工程规范。

## 里程碑 3：诊断报告页面

目标：把“解析结果”与“诊断解释”分开。

当前 `outputs/extraction-report/index.html` 只展示提取结果。后续可以增加：

```text
outputs/extraction-report/
├── index.html        # 文档结构树
├── diagnostics.html  # 标题识别依据和格式问题
├── tree.svg          # 文档树图
└── tree.json         # 原始 JSON
```

`diagnostics.html` 建议包含：

- 标题识别依据表格。
- 样式 ID、样式名称、`outlineLvl` 对照。
- 模板与论文比较结果。
- 问题严重等级：`error`、`warning`、`info`。
- 可操作修复建议。

## 里程碑 4：示例与演示资产

目标：让别人打开仓库后能快速理解项目价值。

建议新增：

```text
examples/
├── analyze.sh
├── compare.sh
├── apply-style.sh
├── sample-tree.json
├── sample-compare-report.json
└── screenshots/
```

README 顶部可以继续强化：

- 一句话说明项目解决什么问题。
- 一张 `DOCX -> 结构树 -> 格式报告` 流程图。
- 一张模板比较报告截图。
- 一个最小可运行示例。

这些做法常见于受欢迎的开源项目：先让读者看到效果，再给出安装和 API。

## 里程碑 5：批量检查与命令行增强

目标：支持课程或实验室批量检查多份论文。

建议 CLI：

```bash
uv run python cli.py compare template.docx paper.docx -o report.json
uv run python cli.py batch-compare template.docx submissions/ -o reports/
```

输出：

```text
reports/
├── summary.csv
├── paper-a.json
├── paper-b.json
└── paper-c.json
```

第一版只需要生成 JSON 和 CSV，不必做复杂后台任务系统。

## 里程碑 6：部署与复现

目标：让项目更容易被他人运行。

建议新增：

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- GitHub Actions 中的 release artifact 或测试报告

示例命令：

```bash
docker compose up
```

服务启动后即可访问：

```text
http://127.0.0.1:8000/docs
```

## 非目标范围

为了不超出课程题目，以下能力不纳入主线：

- PDF 解析、OCR 或扫描件识别。
- 论文查重、语义相似度检测。
- AI 自动写作、润色或内容评价。
- 完整复刻 Microsoft Word 排版渲染。
- 在线多人协作文档编辑。
- 通用办公套件或文档管理系统。

这些能力虽然听起来有吸引力，但会稀释项目重点，也不利于在课程报告中讲清楚核心技术。

## 推荐优先级

| 优先级 | 任务 | 原因 |
|---|---|---|
| P0 | `/api/v1/compare` 模板一致性比较 | 最能体现实际应用价值。 |
| P0 | 比较报告 JSON 和 HTML 页面 | 直接服务演示和课程报告。 |
| P1 | Pydantic API Schema | 提升 API 专业度和可维护性。 |
| P1 | 示例目录和截图 | 增强 README 吸引力。 |
| P2 | 批量检查 CLI | 适合课程批改和实验室场景。 |
| P2 | Docker 部署 | 提升复现便利性。 |

## 一句话愿景

让 Word 论文像代码一样可解析、可检查、可规范化。
