"""Advisory run use case — execute graph and persist results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.agents.context import load_advisory_context
from app.agents.contracts import AgentResult
from app.agents.graph import ADVISORY_GRAPH
from app.agents.notification import run_notification_agent
from app.core.config import Settings
from app.domain.enums import AdvisoryRunStatus
from app.infrastructure.db.models import (
    AdvisoryRunModel,
    AgentResultModel,
    RecommendationExplanationModel,
    RecommendationModel,
)


@dataclass
class AdvisoryRunResult:
    run_id: int
    status: str
    recommendations_count: int
    actionable_count: int
    warnings: List[str]
    error_message: Optional[str] = None
    email_status: Optional[str] = None
    notification_id: Optional[int] = None


def _persist_agent(db: Session, run_id: int, result: AgentResult) -> None:
    db.add(
        AgentResultModel(
            run_id=run_id,
            agent_name=result.agent_name,
            confidence=Decimal(str(round(result.confidence, 4))),
            latency_ms=result.latency_ms,
            payload={
                "signals": result.signals,
                "evidence": [e.model_dump() for e in result.evidence],
                "payload": result.payload,
                "version": result.version,
                "as_of": result.as_of.isoformat(),
            },
            warnings=result.warnings,
        )
    )


def execute_advisory_run(
    db: Session,
    settings: Settings,
    trigger: str = "on_demand",
    notify_email: Optional[bool] = None,
) -> AdvisoryRunResult:
    as_of = datetime.now(timezone.utc)
    should_email = settings.email_notify_on_run if notify_email is None else notify_email

    run = AdvisoryRunModel(
        trigger=trigger,
        status=AdvisoryRunStatus.RUNNING.value,
        graph_version="v1",
        as_of=as_of,
        meta={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    warnings: List[str] = []
    email_status: Optional[str] = None
    notification_id: Optional[int] = None

    try:
        ctx = load_advisory_context(db, settings)
        warnings.extend(ctx.warnings)

        final_state = ADVISORY_GRAPH.invoke({"context": ctx, "settings": settings})

        research: Dict[str, AgentResult] = final_state["research"]
        for name in ("etf", "technical", "dollar", "dxy", "macro", "portfolio"):
            _persist_agent(db, run.id, research[name])
        for key in ("risk", "strategy", "compliance", "explanation"):
            _persist_agent(db, run.id, final_state[key])
            warnings.extend(final_state[key].warnings)

        compliance = final_state["compliance"]
        explanation = final_state["explanation"]
        expl_by_symbol = {
            e["symbol"]: e for e in explanation.payload.get("explanations", [])
        }

        actionable = 0
        recs = compliance.payload.get("recommendations", [])
        for rec in recs:
            if rec["action"] != "HOLD":
                actionable += 1
            row = RecommendationModel(
                run_id=run.id,
                symbol=rec["symbol"],
                action=rec["action"],
                size_pct=Decimal(str(rec.get("size_pct") or 0)),
                size_amount_usd=Decimal(str(rec.get("size_amount_usd") or 0)),
                confidence=Decimal(str(round(float(rec.get("confidence") or 0), 4))),
                status="published",
                compliance_status=rec.get("compliance_status") or "approved",
                feature_snapshot_ref=f"market_features:{rec['symbol']}:v1",
            )
            db.add(row)
            db.flush()
            expl = expl_by_symbol.get(rec["symbol"])
            if expl:
                db.add(
                    RecommendationExplanationModel(
                        recommendation_id=row.id,
                        locale=expl.get("locale", "es"),
                        thesis=expl.get("thesis", ""),
                        risks=expl.get("risks", ""),
                        invalidation=expl.get("invalidation"),
                        evidence_refs=expl.get("evidence_refs") or [],
                    )
                )

        if should_email:
            persisted = db.scalars(
                select(RecommendationModel)
                .options(selectinload(RecommendationModel.explanation))
                .where(RecommendationModel.run_id == run.id)
            ).all()
            notif = run_notification_agent(
                db,
                settings,
                run_id=run.id,
                recommendations=list(persisted),
                as_of=as_of,
            )
            _persist_agent(db, run.id, notif)
            warnings.extend(notif.warnings)
            email_status = notif.payload.get("status")
            notification_id = notif.payload.get("notification_id")

        run.status = AdvisoryRunStatus.COMPLETED.value
        run.finished_at = datetime.now(timezone.utc)
        run.meta = {
            "warnings": sorted(set(warnings)),
            "email_status": email_status,
            "notification_id": notification_id,
        }
        db.commit()

        return AdvisoryRunResult(
            run_id=run.id,
            status=run.status,
            recommendations_count=len(recs),
            actionable_count=actionable,
            warnings=sorted(set(warnings)),
            email_status=email_status,
            notification_id=notification_id,
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        run = db.get(AdvisoryRunModel, run.id)
        if run is not None:
            run.status = AdvisoryRunStatus.FAILED.value
            run.error_message = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            run_id = run.id
        else:
            run_id = -1
        return AdvisoryRunResult(
            run_id=run_id,
            status=AdvisoryRunStatus.FAILED.value,
            recommendations_count=0,
            actionable_count=0,
            warnings=warnings,
            error_message=str(exc),
            email_status=email_status,
            notification_id=notification_id,
        )
