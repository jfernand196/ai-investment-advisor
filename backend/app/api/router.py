from fastapi import APIRouter, Depends

from app.api.routes import admin, advisory, etfs, health, market, meta, portfolio, profile
from app.core.security import require_api_key

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])

protected = APIRouter(dependencies=[Depends(require_api_key)])
protected.include_router(meta.router, tags=["meta"])
protected.include_router(profile.router, tags=["profile"])
protected.include_router(portfolio.router, tags=["portfolios"])
protected.include_router(etfs.router, tags=["etfs"])
protected.include_router(market.router, tags=["market"])
protected.include_router(advisory.router, tags=["advisory"])
protected.include_router(admin.router, tags=["admin"])
api_router.include_router(protected)
