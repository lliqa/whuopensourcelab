import {
  ArrowRight,
  BarChart3,
  Braces,
  ChevronRight,
  FileText,
  ListTree,
  Loader2,
  Maximize2,
  Minimize2,
  Network,
  Play,
  Server,
  UploadCloud
} from "lucide-react";
import { useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

const REASON_LABELS = {
  paragraph_outline: "段落大纲层级",
  style_outline: "样式大纲层级",
  style_id: "样式 ID",
  style_name: "样式名称",
  title_style: "题名样式"
};

const DEFAULT_PIPELINE = [
  "解包 DOCX",
  "解析 OOXML",
  "建立样式索引",
  "识别结构角色",
  "栈式构建树",
  "输出结果"
];

const VIEW_META = {
  tree: {
    icon: ListTree,
    label: "文档树",
    title: "文档树结构"
  },
  flow: {
    icon: Network,
    label: "解析流程",
    title: "解析流程"
  },
  api: {
    icon: Server,
    label: "服务接口",
    title: "服务封装"
  }
};

function countContent(node) {
  if (!node) {
    return 0;
  }
  return (
    (node.content?.length ?? 0) +
    (node.children ?? []).reduce((total, child) => total + countContent(child), 0)
  );
}

function maxLevel(node) {
  if (!node) {
    return 0;
  }
  return Math.max(node.level ?? 0, ...(node.children ?? []).map((child) => maxLevel(child)));
}

function App() {
  const [result, setResult] = useState(null);
  const [fileName, setFileName] = useState("真实论文模板样例");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [activeView, setActiveView] = useState("tree");
  const [expanded, setExpanded] = useState(false);
  const inputRef = useRef(null);

  const metadata = result?.metadata ?? {};
  const pipeline = result?.algorithm?.pipeline ?? DEFAULT_PIPELINE.map((name) => ({ name }));
  const summary = useMemo(
    () => ({
      nodes: result?.node_count ?? 0,
      headings: metadata.heading_count ?? 0,
      maxLevel: maxLevel(result?.tree),
      content: metadata.content_block_count ?? countContent(result?.tree),
      paragraphs: metadata.paragraph_count ?? 0,
      tables: metadata.table_count ?? 0
    }),
    [metadata, result]
  );
  const activeMeta = VIEW_META[activeView];
  const ActiveIcon = activeMeta.icon;

  async function loadSample() {
    setStatus("loading");
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/v1/demo/sample`);
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const data = await response.json();
      setResult(data);
      setFileName(data.demo?.filename ?? "真实论文模板样例");
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载样例失败");
    } finally {
      setStatus("idle");
    }
  }

  async function analyzeFile(file) {
    if (!file) {
      return;
    }
    setStatus("uploading");
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      const response = await fetch(`${API_BASE}/api/v1/analyze`, {
        method: "POST",
        body: form
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      setResult(await response.json());
      setFileName(file.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "解析上传文件失败");
    } finally {
      setStatus("idle");
    }
  }

  function onDrop(event) {
    event.preventDefault();
    analyzeFile(event.dataTransfer.files?.[0]);
  }

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">DOCX Structure Service</p>
          <h1>DocxStruct 演示台</h1>
        </div>
        <div className="endpoint-pill">FastAPI / React / MCP</div>
      </section>

      <section className={expanded ? "workspace workspace-expanded" : "workspace"}>
        <aside className="panel upload-panel">
          <div className="panel-title">
            <UploadCloud size={20} />
            <span>输入文档</span>
          </div>

          <button className="primary-action" onClick={loadSample} disabled={status !== "idle"}>
            {status === "loading" ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
            加载论文模板样例
          </button>

          <button className="drop-zone" onClick={() => inputRef.current?.click()} onDrop={onDrop} onDragOver={(event) => event.preventDefault()}>
            <FileText size={34} />
            <strong>{fileName}</strong>
            <span>拖拽 DOCX 到这里，或点击选择文件</span>
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".docx"
            hidden
            onChange={(event) => analyzeFile(event.target.files?.[0])}
          />

          <div className="service-box">
            <div className="service-line">
              <span>POST</span>
              <code>/api/v1/analyze</code>
            </div>
            <div className="service-line">
              <span>GET</span>
              <code>/api/v1/demo/sample</code>
            </div>
            <div className="service-line">
              <span>MCP</span>
              <code>analyze_docx_path</code>
            </div>
          </div>

          {error ? <p className="error">{error}</p> : null}
        </aside>

        <section className="result-area">
          <div className="metric-grid">
            <Metric label="文档树节点" value={summary.nodes} />
            <Metric label="标题数量" value={summary.headings} />
            <Metric label="最大层级" value={summary.maxLevel} />
            <Metric label="内容块" value={summary.content} />
            <Metric label="段落扫描" value={summary.paragraphs} />
            <Metric label="表格扫描" value={summary.tables} />
          </div>

          <section className={expanded ? "panel stage-panel stage-panel-expanded" : "panel stage-panel"}>
            <div className="stage-header">
              <div className="panel-title">
                <ActiveIcon size={20} />
                <span>{activeMeta.title}</span>
              </div>

              <div className="stage-controls">
                <div className="view-tabs" aria-label="结果视图">
                  {Object.entries(VIEW_META).map(([id, item]) => {
                    const Icon = item.icon;
                    return (
                      <button
                        className={activeView === id ? "view-tab active" : "view-tab"}
                        key={id}
                        onClick={() => setActiveView(id)}
                        type="button"
                      >
                        <Icon size={16} />
                        <span>{item.label}</span>
                      </button>
                    );
                  })}
                </div>
                <button className="ghost-action" onClick={() => setExpanded((value) => !value)} type="button">
                  {expanded ? <Minimize2 size={17} /> : <Maximize2 size={17} />}
                  <span>{expanded ? "收起" : "展开"}</span>
                </button>
              </div>
            </div>

            {activeView === "tree" ? (
              <div className="tree-stage">
                {result?.tree ? (
                  <TreeNode node={result.tree} root />
                ) : (
                  <EmptyState />
                )}
              </div>
            ) : null}

            {activeView === "flow" ? <PipelineView pipeline={pipeline} /> : null}

            {activeView === "api" ? <ServiceView /> : null}
          </section>
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <Braces size={34} />
      <p>加载样例或上传 DOCX 后，这里会显示解析出的文档树。</p>
    </div>
  );
}

function PipelineView({ pipeline }) {
  return (
    <div className="pipeline">
      {pipeline.map((step, index) => (
        <div className="pipeline-step" key={step.id ?? step.name}>
          <div className="step-index">{index + 1}</div>
          <div>
            <strong>{step.name}</strong>
            {step.description ? <p>{step.description}</p> : null}
          </div>
          {index < pipeline.length - 1 ? <ArrowRight className="step-arrow" size={16} /> : null}
        </div>
      ))}
    </div>
  );
}

function ServiceView() {
  const endpoints = [
    {
      method: "POST",
      path: "/api/v1/analyze",
      summary: "上传 DOCX，返回结构树、统计信息和解析依据。"
    },
    {
      method: "GET",
      path: "/api/v1/demo/sample",
      summary: "解析内置论文模板，适合现场演示稳定复现。"
    },
    {
      method: "MCP",
      path: "analyze_docx_path",
      summary: "把同一套解析能力暴露给工具化调用。"
    }
  ];

  return (
    <div className="service-stage">
      <div className="service-summary">
        <BarChart3 size={22} />
        <div>
          <strong>同一个解析内核，多种入口复用</strong>
          <p>React 前端、FastAPI 接口和 MCP 工具只负责输入输出封装，核心解析逻辑集中在 Python 包内。</p>
        </div>
      </div>
      <div className="endpoint-list">
        {endpoints.map((endpoint) => (
          <div className="endpoint-row" key={endpoint.path}>
            <span>{endpoint.method}</span>
            <code>{endpoint.path}</code>
            <p>{endpoint.summary}</p>
            <ChevronRight size={16} />
          </div>
        ))}
      </div>
    </div>
  );
}

function TreeNode({ node, root = false }) {
  const reason = node.detect_reason ? REASON_LABELS[node.detect_reason] ?? node.detect_reason : "";
  return (
    <div className={root ? "tree-node root-node" : "tree-node"}>
      <div className="node-row">
        <span className="node-level">L{node.level}</span>
        <strong>{node.title}</strong>
        {reason ? <span className="reason">{reason}</span> : null}
      </div>
      {node.content?.length ? (
        <div className="content-list">
          {node.content.slice(0, 3).map((item, index) => (
            <span key={`${item.type}-${item.block_index ?? index}`}>
              {item.type === "table" ? "表格" : item.text}
            </span>
          ))}
          {node.content.length > 3 ? <span>还有 {node.content.length - 3} 个内容块</span> : null}
        </div>
      ) : null}
      {node.children?.length ? (
        <div className="children">
          {node.children.map((child, index) => (
            <TreeNode node={child} key={`${child.title}-${child.block_index ?? index}`} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default App;
