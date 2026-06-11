# DocxStruct Demo Frontend

React 单页演示前端，用于现场展示 DOCX 结构化解析结果。

```bash
cd frontend
npm install
npm run dev
```

默认通过 Vite 代理访问 FastAPI：

```text
http://127.0.0.1:5173 -> http://127.0.0.1:8000
```

先启动后端：

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

页面支持两种演示方式：

- 点击“加载论文模板样例”，直接解析仓库内置 fixture。
- 拖拽或选择任意 `.docx` 文件，调用 `/api/v1/analyze` 上传解析。
