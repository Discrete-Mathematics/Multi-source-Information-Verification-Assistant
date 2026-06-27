import type { StreamEvent } from "../types";

const STAGE_LABEL: Record<string, string> = {
  extract: "① 断言抽取",
  plan: "② 检索规划",
  retrieve: "③ 多源检索",
  assess: "④ 证据研判",
  aggregate: "⑤ 裁决聚合",
  report: "⑥ 生成报告",
  done: "✓ 完成",
  error: "✕ 出错",
};

const STAGE_DOT: Record<string, string> = {
  extract: "#6366f1",
  plan: "#0ea5e9",
  retrieve: "#14b8a6",
  assess: "#f59e0b",
  aggregate: "#a855f7",
  report: "#22c55e",
  done: "#22c55e",
  error: "#ef4444",
};

// Live, scrolling trace of pipeline events — the "Agent 执行轨迹".
export function Trace({ events, running }: { events: StreamEvent[]; running: boolean }) {
  return (
    <div className="trace">
      <div className="panel-title">
        实时核验轨迹
        {running && <span className="pulse" />}
      </div>
      <div className="trace-list">
        {events.length === 0 && <div className="muted">等待开始…</div>}
        {events.map((ev, i) => (
          <div className="trace-item" key={i}>
            <span className="trace-dot" style={{ background: STAGE_DOT[ev.stage] || "#64748b" }} />
            <span className="trace-stage">{STAGE_LABEL[ev.stage] || ev.stage}</span>
            <span className="trace-msg">{ev.message}</span>
            {ev.queries && (
              <div className="trace-queries">
                {ev.queries.map((q, j) => (
                  <code key={j}>{q}</code>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
