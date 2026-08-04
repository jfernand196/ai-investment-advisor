from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.infrastructure.db.session import get_db


def settings_dep() -> Settings:
    return get_settings()


DbSession = Depends(get_db)
AppSettings = Depends(settings_dep)


# Re-export for routers
__all__ = ["settings_dep", "get_db", "DbSession", "AppSettings", "Session", "Settings"]
