from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.profile import InvestorProfileOut, InvestorProfileUpdate
from app.core.config import Settings, get_settings
from app.infrastructure.db.models import InvestorProfileHistoryModel, InvestorProfileModel
from app.infrastructure.db.seed import seed_reference_data
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/profile")


def _get_or_seed_profile(db: Session, settings: Settings) -> InvestorProfileModel:
    profile = db.scalar(select(InvestorProfileModel).limit(1))
    if profile is None:
        seed_reference_data(db, settings)
        profile = db.scalar(select(InvestorProfileModel).limit(1))
    if profile is None:
        raise HTTPException(status_code=500, detail="Profile bootstrap failed")
    return profile


@router.get("", response_model=InvestorProfileOut)
def get_profile(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> InvestorProfileModel:
    return _get_or_seed_profile(db, settings)


@router.put("", response_model=InvestorProfileOut)
def update_profile(
    payload: InvestorProfileUpdate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> InvestorProfileModel:
    profile = _get_or_seed_profile(db, settings)
    data = payload.model_dump(exclude_unset=True)

    if not data:
        return profile

    cons = data.get("allocation_conservative_pct", profile.allocation_conservative_pct)
    mod = data.get("allocation_moderate_pct", profile.allocation_moderate_pct)
    agg = data.get("allocation_aggressive_pct", profile.allocation_aggressive_pct)
    if cons + mod + agg != 100:
        raise HTTPException(
            status_code=422,
            detail="allocation_conservative_pct + moderate + aggressive must equal 100",
        )

    before = InvestorProfileOut.model_validate(profile).model_dump(mode="json")

    for key, value in data.items():
        setattr(profile, key, value)
    profile.version += 1

    db.add(
        InvestorProfileHistoryModel(
            profile_id=profile.id,
            version=profile.version,
            snapshot=before,
            change_reason="api_update",
        )
    )
    db.commit()
    db.refresh(profile)
    return profile
