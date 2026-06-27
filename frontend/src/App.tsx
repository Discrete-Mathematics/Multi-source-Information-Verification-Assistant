import { useRef, useState } from "react";
import { startVerify, streamEvents } from "./api";
import type { ClaimResult, StreamEvent, VerificationReport } from "./types";
import { Trace } from "./components/Trace";
import { Gauge } from "./components/Gauge";
import { ClaimCard } from "./components/ClaimCard";

type Mode = "text" | "url" | "file";

const EXAMPLES = [
  "Transformer 模型由 Google 在 2017 年的论文《Attention Is All You Need》中提出,它完全摒弃了循环结构。BERT 是第一个使用 Transformer 的模型。",
  "爱因斯坦于 1921 年因提出相对论而获得诺贝尔物理学奖。",
  "GPT-4 是 OpenAI 在 2023 年发布的大语言模型,拥有一万亿个参数,在所有基准上都超过了人类。",
];

export default function App() {
  const [mode, setMode] = useState<Mode>("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [partial, setPartial] = useState<Record<string, ClaimResult>>({});
  const [report, setReport] = useState<VerificationReport | null>(null);
  const [jobId, setJobId] = useState("");
  const [error, setError] = useState("");
  const closeRef = useRef<null | (() => void)>(null);

  const reset = () => {
    setEvents([]);
    setPartial({});
    setReport(null);
    setError("");
  };

  const run = async () => {
    if (running) return;
    reset();
    setRunning(true);
    try {
      const payload =
        mode === "text"
          ? { text }
          : mode === "url"
          ? { url }
          : { file: file || undefined };
      const { job_id, input_text } = await startVerify(payload);
      setJobId(job_id);
      if (mode !== "text") setText(input_text);

      closeRef.current = streamEvents(
        job_id,
        (ev) => {
          setEvents((prev) => [...prev, ev]);
          if (ev.stage === "aggregate" && ev.result) {
            setPartial((p) => ({ ...p, [ev.result!.claim.id]: ev.result! }));
          }
          if (ev.stage === "done" && ev.report) setReport(ev.report);
        },
        () => setRunning(false),
        (e) => {
          setError(e);
          setRunning(false);
        }
      );
    } catch (e: any) {
      setError(e.message || "请求失败");
      setRunning(false);
    }
  };

  const claims = report ? report.claims : Object.values(partial);

  return (
    <div className="app">
      <header className="hero">
        <h1>多源信息核验助手</h1>
        <p className="sub">
          抽取断言 · 多源检索 · 证据研判 · 可信度评分 · 带引用报告
          <span className="tag">Wikipedia · arXiv · Semantic Scholar · Crossref · Web</span>
        </p>
      </header>

      <div className="layout">
        <section className="left">
          <div className="card input-card">
            <div className="mode-tabs">
              {(["text", "url", "file"] as Mode[]).map((m) => (
                <button
                  key={m}
                  className={mode === m ? "active" : ""}
                  onClick={() => setMode(m)}
                >
                  {m === "text" ? "文本" : m === "url" ? "网址" : "文件"}
                </button>
              ))}
            </div>

            {mode === "text" && (
              <textarea
                placeholder="粘贴一段需要核验的说法、段落或报告…"
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={7}
              />
            )}
            {mode === "url" && (
              <input
                className="url-input"
                placeholder="https://…  (将抓取正文后核验)"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
            )}
            {mode === "file" && (
              <div className="file-input">
                <input
                  type="file"
                  accept=".txt,.md,.markdown"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                <span className="muted small">支持 .txt / .md</span>
              </div>
            )}

            {mode === "text" && (
              <div className="examples">
                <span className="muted small">试试:</span>
                {EXAMPLES.map((ex, i) => (
                  <button key={i} className="ex-btn" onClick={() => setText(ex)}>
                    示例 {i + 1}
                  </button>
                ))}
              </div>
            )}

            <button className="run-btn" onClick={run} disabled={running}>
              {running ? "核验中…" : "开始核验"}
            </button>
            {error && <div className="error">{error}</div>}
          </div>

          <Trace events={events} running={running} />
        </section>

        <section className="right">
          {!report && claims.length === 0 && !running && (
            <div className="empty">
              <div className="empty-icon">🔎</div>
              <p>输入一段文本,系统会拆解其中的关键断言,从多个来源检索证据,逐条给出可解释的核验结论。</p>
            </div>
          )}

          {report && (
            <div className="card overall">
              <Gauge value={report.overall_credibility} />
              <div className="overall-text">
                <div className="overall-verdict">{report.overall_verdict}</div>
                <p>{report.summary}</p>
                <a
                  className="dl-btn"
                  href={`/api/report/${jobId}.md`}
                  target="_blank"
                  rel="noreferrer"
                >
                  ⬇ 下载 Markdown 报告
                </a>
              </div>
            </div>
          )}

          {claims.map((cr, i) => (
            <ClaimCard key={cr.claim.id} cr={cr} jobId={jobId} index={i + 1} />
          ))}

          {report && report.sources.length > 0 && (
            <div className="card sources">
              <div className="panel-title">引用来源 ({report.sources.length})</div>
              <ol>
                {report.sources.map((s) => (
                  <li key={s.id}>
                    <a href={s.url} target="_blank" rel="noreferrer">
                      {s.title}
                    </a>{" "}
                    <span className="muted small">
                      ({s.source}
                      {s.published ? `, ${s.published}` : ""})
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </section>
      </div>
      <footer className="foot">
        中国科学院软件研究所 · 中文信息处理实验室 Coding 测试 · 任务3 多源信息核验助手
      </footer>
    </div>
  );
}
