import { useState } from "react";
import type { AssessedEvidence, ClaimResult } from "../types";
import {
  CLAIM_TYPE_LABEL,
  SOURCE_KIND_COLOR,
  SOURCE_KIND_LABEL,
  SOURCE_NAME_LABEL,
  STANCE_LABEL,
  VERDICT_COLOR,
  VERDICT_LABEL,
  credColor,
} from "../labels";
import { sendFeedback } from "../api";

function EvidenceItem({ a }: { a: AssessedEvidence }) {
  const ev = a.evidence;
  return (
    <a className="ev" href={ev.url} target="_blank" rel="noreferrer">
      <div className="ev-head">
        <span
          className="ev-kind"
          style={{ background: SOURCE_KIND_COLOR[ev.kind] + "22", color: SOURCE_KIND_COLOR[ev.kind] }}
        >
          {SOURCE_NAME_LABEL[ev.source] || ev.source} · {SOURCE_KIND_LABEL[ev.kind]}
        </span>
        {ev.published && <span className="ev-date">{ev.published}</span>}
        <span className="ev-weight" title="综合权重">
          w {a.weight.toFixed(2)}
        </span>
      </div>
      <div className="ev-title">{ev.title}</div>
      {a.note && <div className="ev-note">{a.note}</div>}
      <div className="ev-metrics">
        <Metric label="相关" v={a.relevance} />
        <Metric label="质量" v={a.quality} />
        <Metric label="时效" v={a.recency} />
        <Metric label="立场置信" v={a.stance_confidence} />
      </div>
    </a>
  );
}

function Metric({ label, v }: { label: string; v: number }) {
  return (
    <span className="metric">
      {label}
      <span className="metric-bar">
        <span style={{ width: `${Math.round(v * 100)}%` }} />
      </span>
    </span>
  );
}

export function ClaimCard({ cr, jobId, index }: { cr: ClaimResult; jobId: string; index: number }) {
  const [open, setOpen] = useState(true);
  const [fb, setFb] = useState<boolean | null>(null);

  const supports = cr.evidence.filter((e) => e.stance === "supports");
  const refutes = cr.evidence.filter((e) => e.stance === "refutes");
  const neutral = cr.evidence.filter((e) => e.stance === "neutral");
  const color = VERDICT_COLOR[cr.verdict];

  const vote = (ok: boolean) => {
    setFb(ok);
    sendFeedback({ job_id: jobId, claim_id: cr.claim.id, verdict_correct: ok }).catch(() => {});
  };

  return (
    <div className="claim-card" style={{ borderLeftColor: color }}>
      <div className="claim-head" onClick={() => setOpen(!open)}>
        <span className="claim-idx">{index}</span>
        <span className="claim-text">{cr.claim.text}</span>
        <span className="verdict-badge" style={{ background: color }}>
          {VERDICT_LABEL[cr.verdict]}
        </span>
      </div>

      <div className="claim-meta">
        <span className="chip">{CLAIM_TYPE_LABEL[cr.claim.type] || cr.claim.type}</span>
        <span className="cred" style={{ color: credColor(cr.credibility) }}>
          可信度 {cr.credibility.toFixed(0)}
        </span>
        <div className="cred-bar">
          <span
            style={{ width: `${cr.credibility}%`, background: credColor(cr.credibility) }}
          />
        </div>
        <span className="muted">置信 {cr.confidence.toFixed(2)}</span>
      </div>

      <div className="explanation">{cr.explanation}</div>

      <div className="claim-actions">
        <button className="link-btn" onClick={() => setOpen(!open)}>
          {open ? "收起证据" : `展开证据 (${cr.evidence.length})`}
        </button>
        <span className="fb">
          这条裁决对吗?
          <button className={fb === true ? "on" : ""} onClick={() => vote(true)}>
            👍
          </button>
          <button className={fb === false ? "on" : ""} onClick={() => vote(false)}>
            👎
          </button>
          {fb !== null && <span className="muted">已记录,谢谢反馈</span>}
        </span>
      </div>

      {open && (
        <div className="conflict">
          <div className="conflict-col support">
            <div className="col-head">支持 ({supports.length})</div>
            {supports.length === 0 && <div className="muted small">无</div>}
            {supports.map((a) => (
              <EvidenceItem key={a.evidence.id} a={a} />
            ))}
          </div>
          <div className="conflict-col refute">
            <div className="col-head">反驳 ({refutes.length})</div>
            {refutes.length === 0 && <div className="muted small">无</div>}
            {refutes.map((a) => (
              <EvidenceItem key={a.evidence.id} a={a} />
            ))}
          </div>
          <div className="conflict-col neutral">
            <div className="col-head">中立/相关 ({neutral.length})</div>
            {neutral.length === 0 && <div className="muted small">无</div>}
            {neutral.map((a) => (
              <EvidenceItem key={a.evidence.id} a={a} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
