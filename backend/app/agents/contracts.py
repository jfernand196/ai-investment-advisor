"""Shared multi-agent contracts (Pydantic)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    source: str
    ref_id: str
    summary: str


class AgentResult(BaseModel):
    agent_name: str
    version: str = "v1"
    as_of: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    latency_ms: int = 0
    payload: Dict[str, Any] = Field(default_factory=dict)


class RecommendationDraft(BaseModel):
    symbol: str
    action: Literal["BUY", "SELL", "HOLD", "INCREASE", "REDUCE"]
    size_pct: float = 0.0
    size_amount_usd: float = 0.0
    confidence: float = 0.5
    rationale_points: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    compliance_status: Literal["approved", "adjusted", "rejected"] = "approved"
    compliance_notes: List[str] = Field(default_factory=list)


class ExplanationDraft(BaseModel):
    symbol: str
    thesis: str
    risks: str
    invalidation: str
    evidence_refs: List[str] = Field(default_factory=list)
    locale: str = "es"
