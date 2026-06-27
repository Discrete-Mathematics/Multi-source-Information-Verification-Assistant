import type { Verdict, Stance, SourceKind } from "./types";

export const VERDICT_LABEL: Record<Verdict, string> = {
  supported: "证据支持",
  refuted: "证据反驳",
  partially_supported: "部分支持",
  conflicting: "证据冲突",
  insufficient: "证据不足",
};

export const VERDICT_COLOR: Record<Verdict, string> = {
  supported: "#22c55e",
  refuted: "#ef4444",
  partially_supported: "#f59e0b",
  conflicting: "#a855f7",
  insufficient: "#94a3b8",
};

export const STANCE_LABEL: Record<Stance, string> = {
  supports: "支持",
  refutes: "反驳",
  neutral: "中立",
};

export const SOURCE_KIND_LABEL: Record<SourceKind, string> = {
  peer_reviewed: "同行评审",
  preprint: "预印本",
  encyclopedia: "百科",
  web: "网页",
};

export const SOURCE_KIND_COLOR: Record<SourceKind, string> = {
  peer_reviewed: "#0ea5e9",
  preprint: "#6366f1",
  encyclopedia: "#14b8a6",
  web: "#64748b",
};

export const CLAIM_TYPE_LABEL: Record<string, string> = {
  statistical: "统计数字",
  causal: "因果关系",
  definitional: "定义分类",
  research_finding: "研究结论",
  temporal: "时间事件",
  attribution: "归属主张",
  general_fact: "一般事实",
  opinion: "主观观点",
};

export function credColor(c: number): string {
  if (c >= 70) return "#22c55e";
  if (c >= 45) return "#f59e0b";
  return "#ef4444";
}

export const SOURCE_NAME_LABEL: Record<string, string> = {
  wikipedia: "Wikipedia",
  arxiv: "arXiv",
  semantic_scholar: "Semantic Scholar",
  crossref: "Crossref",
  web: "Web",
};
