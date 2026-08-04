from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.agents.notification import run_notification_agent
from app.api.schemas.advisory import (
    AdvisoryRunCreate,
    AdvisoryRunOut,
    AdvisoryRunSummary,
    NotificationOut,
    RecommendationOut,
)
from app.application.advisory.run import execute_advisory_run
from app.core.config import Settings, get_settings
from app.infrastructure.db.models import AdvisoryRunModel, NotificationModel, RecommendationModel
from app.infrastructure.db.session import get_db

router = APIRouter()


@router.post("/advisory/runs", response_model=AdvisoryRunSummary)
def create_advisory_run(
    payload: Optional[AdvisoryRunCreate] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdvisoryRunSummary:
    body = payload or AdvisoryRunCreate()
    result = execute_advisory_run(
        db,
        settings,
        trigger=body.trigger,
        notify_email=body.notify_email,
    )
    if result.status == "failed":
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Advisory run failed",
                "run_id": result.run_id,
                "error": result.error_message,
            },
        )
    return AdvisoryRunSummary(
        run_id=result.run_id,
        status=result.status,
        recommendations_count=result.recommendations_count,
        actionable_count=result.actionable_count,
        warnings=result.warnings,
        error_message=result.error_message,
        email_status=result.email_status,
        notification_id=result.notification_id,
    )


@router.get("/advisory/runs/{run_id}", response_model=AdvisoryRunOut)
def get_advisory_run(run_id: int, db: Session = Depends(get_db)) -> AdvisoryRunModel:
    run = db.scalar(
        select(AdvisoryRunModel)
        .options(
            selectinload(AdvisoryRunModel.agent_results),
            selectinload(AdvisoryRunModel.recommendations).selectinload(
                RecommendationModel.explanation
            ),
        )
        .where(AdvisoryRunModel.id == run_id)
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/advisory/runs/{run_id}/notify", response_model=NotificationOut)
def notify_advisory_run(
    run_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> NotificationModel:
    run = db.get(AdvisoryRunModel, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    recs = db.scalars(
        select(RecommendationModel)
        .options(selectinload(RecommendationModel.explanation))
        .where(RecommendationModel.run_id == run_id)
    ).all()
    if not recs:
        raise HTTPException(status_code=404, detail="No recommendations for run")

    result = run_notification_agent(
        db,
        settings,
        run_id=run_id,
        recommendations=list(recs),
        as_of=run.as_of,
    )
    db.commit()
    notification = db.get(NotificationModel, result.payload["notification_id"])
    if notification is None:
        raise HTTPException(status_code=500, detail="Notification persist failed")
    return notification


@router.get("/recommendations", response_model=List[RecommendationOut])
def list_recommendations(
    limit: int = Query(default=50, ge=1, le=200),
    actionable_only: bool = Query(default=False),
    run_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> list:
    stmt = (
        select(RecommendationModel)
        .options(selectinload(RecommendationModel.explanation))
        .order_by(desc(RecommendationModel.created_at))
        .limit(limit)
    )
    if run_id is not None:
        stmt = stmt.where(RecommendationModel.run_id == run_id)
    rows = list(db.scalars(stmt).all())
    if actionable_only:
        rows = [r for r in rows if r.action != "HOLD"]
    return rows


@router.get("/notifications", response_model=List[NotificationOut])
def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list:
    stmt = select(NotificationModel).order_by(desc(NotificationModel.created_at)).limit(limit)
    return list(db.scalars(stmt).all())
