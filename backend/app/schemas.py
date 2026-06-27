"""Pydantic models shared across the verification pipeline.

These are the contract between every stage (extraction -> planning ->
retrieval -> assessment -> aggregation -> report) and the API/front-end.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class ClaimType(str, Enum):
    statistical = "statistical"          # 含数字/比例/量级
    causal = "causal"                    # X 导致 Y
    definitional = "definitional"        # 定义/分类
    research_finding = "research_finding"  # 对论文/研究结论的转述
    temporal = "temporal"                # 时间/先后/首次
    attribution = "attribution"          # 某人/某机构 说了/做了 某事
    general_fact = "general_fact"        # 其它一般事实
    opinion = "opinion"                  # 主观观点(不可核验,通常被过滤)


class Stance(str, Enum):
    supports = "supports"
    refutes = "refutes"
    neutral = "neutral"


class Verdict(str, Enum):
    supported = "supported"              # 证据充分支持
    refuted = "refuted"                  # 证据充分反驳
    partially_supported = "partially_supported"
    conflicting = "conflicting"          # 高质量证据互相矛盾
    insufficient = "insufficient"        # 证据不足/检索不到


class SourceKind(str, Enum):
    peer_reviewed = "peer_reviewed"      # 同行评审论文 (Crossref / S2 venue)
    preprint = "preprint"                # 预印本 (arXiv)
    encyclopedia = "encyclopedia"        # 百科 (Wikipedia)
    web = "web"                          # 普通网页


# --------------------------------------------------------------------------- #
# Stage 1 — claim extraction
# --------------------------------------------------------------------------- #
class Claim(BaseModel):
    id: str
    text: str = Field(description="自包含、已消解指代的原子断言")
    type: ClaimType = ClaimType.general_fact
    checkworthiness: float = Field(0.5, ge=0, le=1, description="可核验价值 0-1")
    source_span: Optional[str] = Field(None, description="原文中对应的片段")
    rationale: Optional[str] = Field(None, description="为何拆分/为何值得核验")


# --------------------------------------------------------------------------- #
# Stage 2 — query planning
# --------------------------------------------------------------------------- #
class SearchPlan(BaseModel):
    claim_id: str
    queries: List[str]
    sources: List[str] = Field(description="路由到的证据源名称")


# --------------------------------------------------------------------------- #
# Stage 3 — evidence retrieval
# --------------------------------------------------------------------------- #
class Evidence(BaseModel):
    id: str
    title: str
    snippet: str = Field(description="用于判断立场的文本片段/摘要")
    url: str
    source: str = Field(description="adapter 名称, e.g. arxiv / wikipedia")
    kind: SourceKind = SourceKind.web
    published: Optional[str] = Field(None, description="ISO 日期或年份")
    authors: Optional[List[str]] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None
    query: Optional[str] = Field(None, description="检索到它的查询")


# --------------------------------------------------------------------------- #
# Stage 4 — evidence assessment (evidence x claim)
# --------------------------------------------------------------------------- #
class AssessedEvidence(BaseModel):
    evidence: Evidence
    stance: Stance = Stance.neutral
    stance_confidence: float = Field(0.0, ge=0, le=1)
    relevance: float = Field(0.0, ge=0, le=1)
    quality: float = Field(0.0, ge=0, le=1, description="来源质量(派生自 kind/venue/引用)")
    recency: float = Field(0.0, ge=0, le=1, description="时效性 0-1")
    weight: float = Field(0.0, ge=0, description="综合权重 = relevance*quality*recency*conf")
    note: Optional[str] = Field(None, description="该证据为何支持/反驳的一句话解释")


# --------------------------------------------------------------------------- #
# Stage 5 — aggregation
# --------------------------------------------------------------------------- #
class ClaimResult(BaseModel):
    claim: Claim
    verdict: Verdict = Verdict.insufficient
    credibility: float = Field(0.0, ge=0, le=100, description="断言级可信度评分 0-100")
    confidence: float = Field(0.0, ge=0, le=1, description="系统对自身裁决的信心")
    support_weight: float = 0.0
    refute_weight: float = 0.0
    explanation: str = ""
    evidence: List[AssessedEvidence] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Stage 6 — report
# --------------------------------------------------------------------------- #
class VerificationReport(BaseModel):
    input_text: str
    overall_verdict: str = ""
    overall_credibility: float = 0.0
    summary: str = ""
    claims: List[ClaimResult] = Field(default_factory=list)
    sources: List[Evidence] = Field(default_factory=list)
    markdown: str = ""
