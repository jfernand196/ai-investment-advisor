from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILES = (
    str(ROOT_DIR / ".env"),
    ".env",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "AI Investment Advisor"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"

    app_username: str = "juan"
    app_password: str = "change-me"
    app_secret_key: str = "change-me-to-a-long-random-string"
    # If set, all /api/v1 routes except /health/* require header X-API-Key
    app_api_key: str = ""

    database_url: str = (
        "postgresql+psycopg://advisor:advisor@localhost:5433/ai_investment_advisor"
    )

    llm_provider: str = "lmstudio"
    llm_base_url: str = "http://localhost:1234/v1"
    llm_api_key: str = "lm-studio"
    llm_model: str = "local-model"

    fred_api_key: str = ""
    market_lookback_days: int = 365

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""
    email_notify_on_run: bool = True

    base_currency: str = "USD"
    risk_profile: str = "aggressive"
    allocation_conservative_pct: int = 40
    allocation_moderate_pct: int = 40
    allocation_aggressive_pct: int = 20
    available_capital_usd: float = 10000.0

    etf_universe: List[str] = Field(
        default_factory=lambda: [
            "VOO",
            "VTI",
            "SCHD",
            "QQQ",
            "VGT",
            "VXUS",
            "SMH",
            "SOXL",
            "TQQQ",
        ]
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
