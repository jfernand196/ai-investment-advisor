from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AdvisoryRunCreate(BaseModel):
    trigger: str = Field(default="on_demand")
    notify_email: Optional[bool] = None


class AdvisoryRunSummary(BaseModel):
    run_id: int
    status: str
    recommendations_count: int
    actionable_count: int
    warnings: List[str]
    error_message: Optional[str] = None
    email_status: Optional[str] = None
    notification_id: Optional[int] = None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: str
    status: str
    subject: Optional[str] = None
    body: str
    error_message: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None


class AgentResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_name: str
    confidence: Optional[Decimal] = None
    latency_ms: Optional[int] = None
    payload: Dict[str, Any]
    warnings: List[Any]
    created_at: datetime


class ExplanationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    locale: str
    thesis: str
    risks: str
    invalidation: Optional[str] = None
    evidence_refs: List[Any]


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    symbol: str
    action: str
    size_pct: Optional[Decimal] = None
    size_amount_usd: Optional[Decimal] = None
    confidence: Optional[Decimal] = None
    status: str
    compliance_status: str
    feature_snapshot_ref: Optional[str] = None
    created_at: datetime
    explanation: Optional[ExplanationOut] = None


class AdvisoryRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trigger: str
    status: str
    graph_version: str
    as_of: datetime
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    meta: Dict[str, Any]
    agent_results: List[AgentResultOut] = []
    recommendations: List[RecommendationOut] = []
