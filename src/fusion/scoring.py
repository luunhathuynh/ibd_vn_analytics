from __future__ import annotations

from typing import Any

import pandas as pd

from src.fusion import reason_codes as rc
from src.fusion.rules import (
    build_action_plan,
    determine_final_label,
    market_score_for_status,
    unsafe_composite_snapshot,
)
from src.schemas.llm import (
    CanSlimSnapshot,
    CandlestickSnapshot,
    CompositeSnapshot,
    PaybackSnapshot,
    StockSnapshot,
    StockTechnicalSnapshot,
)


def _technical_reason_codes(row: pd.Series) -> tuple[list[str], list[str], list[str], float]:
    codes: list[str] = []
    positive: list[str] = []
    negative: list[str] = []
    score = float(row.get("rs_score", 0) or 0)

    rs = row.get("rs_score")
    if rs is not None and not pd.isna(rs):
        rs_val = float(rs)
        score = rs_val
        if rs_val >= 90:
            codes.append(rc.RS_SCORE_ABOVE_90)
            positive.append(f"RS score {rs_val:.0f} is elite.")
        elif rs_val >= 80:
            codes.append(rc.RS_SCORE_ABOVE_80)
            positive.append(f"RS score {rs_val:.0f} is strong.")
        elif rs_val >= 70:
            codes.append(rc.RS_SCORE_ABOVE_70)
            positive.append(f"RS score {rs_val:.0f} is above leader threshold.")

    if row.get("above_ma50"):
        codes.append(rc.PRICE_ABOVE_MA50)
        positive.append("Price above MA50.")
        score += 5
    else:
        codes.append(rc.PRICE_BELOW_MA50)
        negative.append("Price below MA50.")
        score -= 10

    if row.get("above_ma200"):
        codes.append(rc.PRICE_ABOVE_MA200)
        positive.append("Price above MA200.")
        score += 5

    if row.get("breakout"):
        codes.append(rc.BREAKOUT_CONFIRMED)
        positive.append("Breakout confirmed with volume.")
        score += 10

    dist = row.get("distance_from_52w_high_pct")
    if dist is not None and not pd.isna(dist) and float(dist) >= -15:
        codes.append(rc.NEAR_52W_HIGH)
        positive.append("Near 52-week high.")

    if row.get("break_ma50"):
        codes.append(rc.WARNING_BREAK_MA50)
        negative.append("Broke below MA50 on recent session.")

    if row.get("warning"):
        codes.append(rc.WARNING_HIGH_VOLUME_SELLING)
        negative.append("High-volume selling warning.")

    score = max(0.0, min(100.0, score))
    return codes, positive, negative, score


def _technical_snapshot(row: pd.Series) -> StockTechnicalSnapshot:
    warning_flags: list[str] = []
    if row.get("break_ma50"):
        warning_flags.append("break_ma50")
    if row.get("warning"):
        warning_flags.append("high_volume_selling")

    breakout_status = "confirmed" if row.get("breakout") else "none"
    codes, _, _, _ = _technical_reason_codes(row)

    return StockTechnicalSnapshot(
        symbol=str(row["ticker"]),
        close=_float_or_none(row.get("close")),
        change_pct=_float_or_none(row.get("change_pct")),
        volume_ratio=_float_or_none(row.get("volume_ratio")),
        rs_score=_float_or_none(row.get("rs_score")),
        above_ma50=bool(row.get("above_ma50")) if not pd.isna(row.get("above_ma50", float("nan"))) else None,
        above_ma200=bool(row.get("above_ma200")) if not pd.isna(row.get("above_ma200", float("nan"))) else None,
        distance_from_52w_high_pct=_float_or_none(row.get("distance_from_52w_high_pct")),
        breakout_status=breakout_status,
        warning_flags=warning_flags,
        reason_codes=codes,
    )


def _float_or_none(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)


def compute_composite_snapshot(
    row: pd.Series,
    market_status: str,
    llm_safe: bool,
    cfg: dict[str, Any],
) -> CompositeSnapshot:
    if not llm_safe:
        return unsafe_composite_snapshot()

    m_score = market_score_for_status(market_status)
    tech_codes, tech_pos, tech_neg, t_score = _technical_reason_codes(row)

    label, instruction = determine_final_label(
        market_status=market_status,
        technical_score=t_score,
        rs_score=_float_or_none(row.get("rs_score")),
        is_breakout=bool(row.get("breakout")),
        has_warning=bool(row.get("break_ma50") or row.get("warning")),
        llm_safe=llm_safe,
    )

    weights = cfg.get("fusion", {}).get("weights", {})
    w_market = float(weights.get("market", 0.25))
    w_technical = float(weights.get("technical", 0.35))
    total_w = w_market + w_technical
    final_score = (m_score * w_market + t_score * w_technical) / total_w if total_w else 0.0

    return CompositeSnapshot(
        market_score=m_score,
        technical_score=t_score,
        canslim_score=None,
        valuation_score=None,
        timing_score=None,
        final_score=round(final_score, 2),
        final_label=label,
        llm_instruction=instruction,
        action_plan=build_action_plan(label),
        positive_reasons=tech_pos,
        negative_reasons=tech_neg,
        reason_codes=tech_codes,
    )


def build_stock_snapshot(
    row: pd.Series,
    market_status: str,
    llm_safe: bool,
    cfg: dict[str, Any],
) -> StockSnapshot:
    technical = _technical_snapshot(row)
    composite = compute_composite_snapshot(row, market_status, llm_safe, cfg)
    return StockSnapshot(
        symbol=str(row["ticker"]),
        sector=str(row.get("sector", "") or ""),
        technical=technical,
        canslim=CanSlimSnapshot(available=False, missing_data=["CANSLIM integration not enabled"]),
        payback=PaybackSnapshot(available=False, missing_data=["Payback integration not enabled"]),
        candlestick=CandlestickSnapshot(available=False, missing_data=["Candlestick integration not enabled"]),
        composite=composite,
        data_quality={"provider_safe": llm_safe},
    )


def snapshots_from_dataframe(
    df: pd.DataFrame,
    market_status: str,
    llm_safe: bool,
    cfg: dict[str, Any],
) -> list[StockSnapshot]:
    if df.empty:
        return []
    return [build_stock_snapshot(row, market_status, llm_safe, cfg) for _, row in df.iterrows()]


def rank_candidates(
    leaders: list[StockSnapshot],
    breakouts: list[StockSnapshot],
    watchlist: list[StockSnapshot],
    limit: int = 20,
) -> list[StockSnapshot]:
    seen: set[str] = set()
    merged: list[StockSnapshot] = []
    for group in (breakouts, leaders, watchlist):
        for snap in group:
            if snap.symbol not in seen:
                seen.add(snap.symbol)
                merged.append(snap)
    merged.sort(key=lambda s: s.composite.final_score, reverse=True)
    return merged[:limit]
