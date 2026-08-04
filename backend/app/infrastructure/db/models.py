"""SQLAlchemy models — Architecture v1.0 personal edition (P0.2)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.session import Base


class InvestorProfileModel(Base):
    __tablename__ = "investor_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    base_currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    risk_profile: Mapped[str] = mapped_column(String(32), default="aggressive", nullable=False)
    available_capital_usd: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("10000.00"), nullable=False
    )
    allocation_conservative_pct: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    allocation_moderate_pct: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    allocation_aggressive_pct: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    investment_horizon: Mapped[str] = mapped_column(String(32), default="long", nullable=False)
    favorite_etfs: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    financial_goals: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    notification_email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    history: Mapped[list[InvestorProfileHistoryModel]] = relationship(back_populates="profile")
    portfolios: Mapped[list[PortfolioModel]] = relationship(back_populates="profile")


class InvestorProfileHistoryModel(Base):
    """SCD Type-2 history for profile changes (auditability)."""

    __tablename__ = "investor_profile_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("investor_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    change_reason: Mapped[Optional[str]] = mapped_column(String(255))

    profile: Mapped[InvestorProfileModel] = relationship(back_populates="history")

    __table_args__ = (UniqueConstraint("profile_id", "version", name="uq_profile_history_version"),)


class PortfolioModel(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("investor_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), default="Primary", nullable=False)
    base_currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    cash_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    profile: Mapped[InvestorProfileModel] = relationship(back_populates="portfolios")
    holdings: Mapped[list[HoldingModel]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list[PortfolioSnapshotModel]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )


class HoldingModel(Base):
    __tablename__ = "holdings"
    __table_args__ = (UniqueConstraint("portfolio_id", "symbol", name="uq_holdings_portfolio_symbol"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"), nullable=False)
    avg_cost_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    portfolio: Mapped[PortfolioModel] = relationship(back_populates="holdings")


class PortfolioSnapshotModel(Base):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "as_of", name="uq_portfolio_snapshot_as_of"),
        Index("ix_portfolio_snapshots_as_of", "as_of"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    nav_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cash_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    weights: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    bucket_weights: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    portfolio: Mapped[PortfolioModel] = relationship(back_populates="snapshots")


class EtfUniverseModel(Base):
    __tablename__ = "etf_universe"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    risk_bucket: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    max_allocation_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    is_leveraged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PriceBarModel(Base):
    __tablename__ = "price_bars"
    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "ts", name="uq_price_bars_symbol_tf_ts"),
        Index("ix_price_bars_symbol_ts", "symbol", "ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), default="1D", nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[Optional[Decimal]] = mapped_column(Numeric(24, 2))
    source: Mapped[str] = mapped_column(String(32), default="yfinance", nullable=False)


class FxRateModel(Base):
    __tablename__ = "fx_rates"
    __table_args__ = (
        UniqueConstraint("pair", "ts", name="uq_fx_rates_pair_ts"),
        Index("ix_fx_rates_pair_ts", "pair", "ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pair: Mapped[str] = mapped_column(String(16), nullable=False)  # USDCOP, DXY proxy, etc.
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="yfinance", nullable=False)


class MacroSeriesModel(Base):
    __tablename__ = "macro_series"
    __table_args__ = (
        UniqueConstraint("series_id", "ts", name="uq_macro_series_id_ts"),
        Index("ix_macro_series_id_ts", "series_id", "ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    series_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ts: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="fred", nullable=False)


class MarketFeatureModel(Base):
    __tablename__ = "market_features"
    __table_args__ = (
        UniqueConstraint(
            "entity", "feature_set_version", "ts", name="uq_market_features_entity_version_ts"
        ),
        Index("ix_market_features_entity_ts", "entity", "ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity: Mapped[str] = mapped_column(String(64), nullable=False)  # symbol or USDCOP/DXY/MACRO
    feature_set_version: Mapped[str] = mapped_column(String(32), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class NewsArticleModel(Base):
    __tablename__ = "news_articles"
    __table_args__ = (
        UniqueConstraint("raw_hash", name="uq_news_articles_raw_hash"),
        Index("ix_news_articles_published_at", "published_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1024))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    raw_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    symbol_maps: Mapped[list[NewsSymbolMapModel]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )
    sentiments: Mapped[list[SentimentScoreModel]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )


class NewsSymbolMapModel(Base):
    __tablename__ = "news_symbol_map"
    __table_args__ = (UniqueConstraint("article_id", "symbol", name="uq_news_symbol_map"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    article: Mapped[NewsArticleModel] = relationship(back_populates="symbol_maps")


class SentimentScoreModel(Base):
    __tablename__ = "sentiment_scores"
    __table_args__ = (
        UniqueConstraint("article_id", "symbol", name="uq_sentiment_article_symbol"),
        Index("ix_sentiment_scores_symbol_created", "symbol", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[Optional[str]] = mapped_column(String(16))  # null = market-wide
    score: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)  # -1 .. 1
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    article: Mapped[NewsArticleModel] = relationship(back_populates="sentiments")


class AdvisoryRunModel(Base):
    __tablename__ = "advisory_runs"
    __table_args__ = (Index("ix_advisory_runs_started_at", "started_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)  # scheduled|on_demand
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    graph_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    agent_results: Mapped[list[AgentResultModel]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list[RecommendationModel]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class AgentResultModel(Base):
    __tablename__ = "agent_results"
    __table_args__ = (
        UniqueConstraint("run_id", "agent_name", name="uq_agent_results_run_agent"),
        Index("ix_agent_results_agent_name", "agent_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("advisory_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    warnings: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped[AdvisoryRunModel] = relationship(back_populates="agent_results")


class RecommendationModel(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index("ix_recommendations_symbol_created", "symbol", "created_at"),
        Index("ix_recommendations_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("advisory_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    size_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    size_amount_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(String(32), default="published", nullable=False)
    compliance_status: Mapped[str] = mapped_column(String(32), default="approved", nullable=False)
    feature_snapshot_ref: Mapped[Optional[str]] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped[AdvisoryRunModel] = relationship(back_populates="recommendations")
    explanation: Mapped[Optional[RecommendationExplanationModel]] = relationship(
        back_populates="recommendation", uselist=False, cascade="all, delete-orphan"
    )
    outcomes: Mapped[list[RecommendationOutcomeModel]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )


class RecommendationExplanationModel(Base):
    __tablename__ = "recommendation_explanations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    locale: Mapped[str] = mapped_column(String(8), default="es", nullable=False)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    risks: Mapped[str] = mapped_column(Text, nullable=False)
    invalidation: Mapped[Optional[str]] = mapped_column(Text)
    evidence_refs: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    recommendation: Mapped[RecommendationModel] = relationship(back_populates="explanation")


class RecommendationOutcomeModel(Base):
    __tablename__ = "recommendation_outcomes"
    __table_args__ = (
        UniqueConstraint(
            "recommendation_id", "horizon_days", name="uq_recommendation_outcome_horizon"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    realized_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    hit: Mapped[Optional[bool]] = mapped_column(Boolean)
    measured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    recommendation: Mapped[RecommendationModel] = relationship(back_populates="outcomes")


class NotificationModel(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_channel_created", "channel", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)  # email|dashboard
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    subject: Mapped[Optional[str]] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(128))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity_created", "entity_type", "entity_id", "created_at"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(64))
    before: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    after: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    actor: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    request_id: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MemoryModel(Base):
    __tablename__ = "memories"
    __table_args__ = (Index("ix_memories_kind_created", "kind", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    # pgvector later; keep null-friendly text embedding ref for now
    embedding_ref: Mapped[Optional[str]] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
