// Mirrors backend/app/schemas.py

export type Verdict =
  | "supported"
  | "refuted"
  | "partially_supported"
  | "conflicting"
  | "insufficient";

export type Stance = "supports" | "refutes" | "neutral";

export type SourceKind = "peer_reviewed" | "preprint" | "encyclopedia" | "web";

export interface Claim {
  id: string;
  text: string;
  type: string;
  checkworthiness: number;
  source_span?: string | null;
  rationale?: string | null;
}

export interface Evidence {
  id: string;
  title: string;
  snippet: string;
  url: string;
  source: string;
  kind: SourceKind;
  published?: string | null;
  authors?: string[] | null;
  venue?: string | null;
  citation_count?: number | null;
  query?: string | null;
}

export interface AssessedEvidence {
  evidence: Evidence;
  stance: Stance;
  stance_confidence: number;
  relevance: number;
  quality: number;
  recency: number;
  weight: number;
  note?: string | null;
}

export interface ClaimResult {
  claim: Claim;
  verdict: Verdict;
  credibility: number;
  confidence: number;
  support_weight: number;
  refute_weight: number;
  explanation: string;
  evidence: AssessedEvidence[];
}

export interface VerificationReport {
  input_text: string;
  overall_verdict: string;
  overall_credibility: number;
  summary: string;
  claims: ClaimResult[];
  sources: Evidence[];
  markdown: string;
}

export interface StreamEvent {
  stage: string;
  status?: string;
  message?: string;
  claim_id?: string;
  queries?: string[];
  sources?: string[];
  count?: number;
  claims?: Claim[];
  result?: ClaimResult;
  report?: VerificationReport;
}
