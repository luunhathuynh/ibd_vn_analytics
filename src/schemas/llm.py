from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

LLM_CONTRACT_VERSION = "1.0.0"


class DataStatus(BaseModel):
    provider: str
    is_real_data: bool
    fallback_used: bool
    llm_safe_to_analyze: bool
    last_successful_update: str | None = None
    report_date: str = ""
    missing_symbols: list[str] = Field(default_factory=list)
    failed_symbols: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    is_stale: bool = False
    generated_at: str | None = None


class MarketContext(BaseModel):
    status: str
    risk_mode: str
    new_buy_allowed: bool
    distribution_day_count: int | None = None
    follow_through_day_detected: bool | None = None
    follow_through_day_date: str | None = None
    summary_points: list[str] = Field(default_factory=list)
    positive_reasons: list[str] = Field(default_factory=list)
    negative_reasons: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class IndexSnapshot(BaseModel):
    symbol: str
    close: float | None = None
    change_pct: float | None = None
    volume_change_pct: float | None = None
    above_ma20: bool | None = None
    above_ma50: bool | None = None
    above_ma200: bool | None = None
    ma_trend: str | None = None
    warnings: list[str] = Field(default_factory=list)


class BreadthSnapshot(BaseModel):
    advancers: int | None = None
    decliners: int | None = None
    unchanged: int | None = None
    advance_decline_ratio: float | None = None
    pct_above_ma50: float | None = None
    pct_above_ma200: float | None = None
    new_high_ratio: float | None = None
    summary: str | None = None


class SectorSnapshot(BaseModel):
    sector: str
    rs_score: float | None = None
    relative_performance_pct: float | None = None
    rank: int | None = None
    leaders: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StockTechnicalSnapshot(BaseModel):
    symbol: str
    close: float | None = None
    change_pct: float | None = None
    volume_ratio: float | None = None
    rs_score: float | None = None
    above_ma50: bool | None = None
    above_ma200: bool | None = None
    distance_from_52w_high_pct: float | None = None
    breakout_status: str = "none"
    warning_flags: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class CanSlimSnapshot(BaseModel):
    available: bool = False
    score: float | None = None
    passed: bool | None = None
    earnings_growth_score: float | None = None
    sales_growth_score: float | None = None
    roe_score: float | None = None
    relative_strength_score: float | None = None
    market_alignment: str | None = None
    positive_reasons: list[str] = Field(default_factory=list)
    negative_reasons: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)


class PaybackSnapshot(BaseModel):
    available: bool = False
    valuation_status: str | None = None
    sticker_price: float | None = None
    mos_50: float | None = None
    mos_60: float | None = None
    mos_70: float | None = None
    current_price: float | None = None
    quality_flags: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)


class CandlestickSnapshot(BaseModel):
    available: bool = False
    signal: str | None = None
    pattern: str | None = None
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    rr: float | None = None
    confidence_score: float | None = None
    confirmation_candle_date: str | None = None
    positive_reasons: list[str] = Field(default_factory=list)
    negative_reasons: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)


class CompositeSnapshot(BaseModel):
    market_score: float = 0.0
    technical_score: float = 0.0
    canslim_score: float | None = None
    valuation_score: float | None = None
    timing_score: float | None = None
    final_score: float = 0.0
    final_label: str = "low_priority"
    llm_instruction: str = ""
    action_plan: dict[str, Any] = Field(default_factory=dict)
    positive_reasons: list[str] = Field(default_factory=list)
    negative_reasons: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class StockSnapshot(BaseModel):
    symbol: str
    sector: str = ""
    technical: StockTechnicalSnapshot
    canslim: CanSlimSnapshot = Field(default_factory=CanSlimSnapshot)
    payback: PaybackSnapshot = Field(default_factory=PaybackSnapshot)
    candlestick: CandlestickSnapshot = Field(default_factory=CandlestickSnapshot)
    composite: CompositeSnapshot
    data_quality: dict[str, Any] = Field(default_factory=dict)


class DailyMarketReportJson(BaseModel):
    llm_contract_version: str = LLM_CONTRACT_VERSION
    report_date: str
    generated_at: str
    data_status: DataStatus
    market_context: MarketContext
    indexes: list[IndexSnapshot] = Field(default_factory=list)
    breadth: BreadthSnapshot
    sectors: list[SectorSnapshot] = Field(default_factory=list)
    leaders: list[StockSnapshot] = Field(default_factory=list)
    breakouts: list[StockSnapshot] = Field(default_factory=list)
    watchlist: list[StockSnapshot] = Field(default_factory=list)
    warnings: list[StockSnapshot] = Field(default_factory=list)
    top_candidates: list[StockSnapshot] = Field(default_factory=list)
    excluded_symbols: list[dict[str, Any]] = Field(default_factory=list)


class CandidatesResponse(BaseModel):
    report_date: str
    generated_at: str
    data_status: DataStatus
    market_context: MarketContext
    candidates: list[StockSnapshot] = Field(default_factory=list)


class ExplainResponse(BaseModel):
    symbol: str
    report_date: str
    final_label: str
    positive_reasons: list[str] = Field(default_factory=list)
    negative_reasons: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    llm_instruction: str = ""
