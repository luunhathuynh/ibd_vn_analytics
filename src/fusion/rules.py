from __future__ import annotations

from typing import Any

from src.fusion import reason_codes as rc
from src.schemas.llm import CompositeSnapshot, MarketContext

MARKET_SCORES: dict[str, float] = {
    "Confirmed Uptrend": 100.0,
    "Rally Attempt": 50.0,
    "Uptrend Under Pressure": 35.0,
    "Market in Correction": 0.0,
}

RISK_MODE: dict[str, str] = {
    "Confirmed Uptrend": "risk_on",
    "Rally Attempt": "wait_for_confirmation",
    "Uptrend Under Pressure": "risk_reduced",
    "Market in Correction": "risk_off",
}

NEW_BUY_ALLOWED: dict[str, bool] = {
    "Confirmed Uptrend": True,
    "Rally Attempt": False,
    "Uptrend Under Pressure": False,
    "Market in Correction": False,
}


def build_market_context(status: str, distribution_days: int, ftd_date: str | None, note: str) -> MarketContext:
    positive: list[str] = []
    negative: list[str] = []
    codes: list[str] = []
    summary = [note] if note else []

    if status == "Confirmed Uptrend":
        codes.append(rc.MARKET_CONFIRMED_UPTREND)
        positive.append("Market in confirmed uptrend.")
        codes.append(rc.MARKET_NEW_BUY_ALLOWED)
    elif status == "Rally Attempt":
        codes.append(rc.MARKET_RALLY_ATTEMPT)
        negative.append("Market in rally attempt — wait for follow-through day.")
        codes.append(rc.MARKET_NEW_BUY_NOT_ALLOWED)
    elif status == "Uptrend Under Pressure":
        codes.append(rc.MARKET_UNDER_PRESSURE)
        negative.append("Uptrend under pressure from distribution days.")
        codes.append(rc.MARKET_NEW_BUY_NOT_ALLOWED)
    else:
        codes.append(rc.MARKET_CORRECTION)
        negative.append("Market in correction — preserve capital.")
        codes.append(rc.MARKET_NEW_BUY_NOT_ALLOWED)

    return MarketContext(
        status=status,
        risk_mode=RISK_MODE.get(status, "risk_off"),
        new_buy_allowed=NEW_BUY_ALLOWED.get(status, False),
        distribution_day_count=distribution_days,
        follow_through_day_detected=ftd_date is not None,
        follow_through_day_date=ftd_date,
        summary_points=summary,
        positive_reasons=positive,
        negative_reasons=negative,
        reason_codes=codes,
    )


def market_score_for_status(status: str) -> float:
    return MARKET_SCORES.get(status, 0.0)


def unsafe_composite_snapshot() -> CompositeSnapshot:
    return CompositeSnapshot(
        market_score=0.0,
        technical_score=0.0,
        canslim_score=None,
        valuation_score=None,
        timing_score=None,
        final_score=0.0,
        final_label="data_not_safe",
        llm_instruction=rc.UNSAFE_LLM_INSTRUCTION,
        action_plan={
            "label": "data_not_safe",
            "allowed_actions": ["watch"],
            "invalid_if": ["Data source is not verified real market data"],
            "risk_management": {
                "max_position_size_pct": None,
                "stop_loss_pct": None,
                "notes": rc.UNSAFE_LLM_INSTRUCTION,
            },
        },
        positive_reasons=[],
        negative_reasons=[rc.UNSAFE_NEGATIVE_REASON],
        reason_codes=[rc.DATA_NOT_SAFE_FOR_LLM],
    )


def build_action_plan(label: str) -> dict[str, Any]:
    plans: dict[str, dict[str, Any]] = {
        "actionable_candidate": {
            "label": "actionable_candidate",
            "allowed_actions": ["watch", "plan_entry"],
            "invalid_if": [
                "Market status changes to Market in Correction",
                "Price closes below MA50",
                "Breakout volume is not confirmed",
            ],
            "risk_management": {"max_position_size_pct": 5.0, "stop_loss_pct": 7.0, "notes": "Use confirmed entry with risk management."},
        },
        "watch_for_setup": {
            "label": "watch_for_setup",
            "allowed_actions": ["watch"],
            "invalid_if": [
                "Market status changes to Market in Correction",
                "Price closes below MA50",
            ],
            "risk_management": {"max_position_size_pct": None, "stop_loss_pct": None, "notes": "No confirmed entry signal yet."},
        },
        "breakout_watch": {
            "label": "breakout_watch",
            "allowed_actions": ["watch"],
            "invalid_if": ["Breakout fails on volume", "Market enters correction"],
            "risk_management": {"max_position_size_pct": None, "stop_loss_pct": 7.0, "notes": "Monitor breakout confirmation."},
        },
        "avoid_new_buy": {
            "label": "avoid_new_buy",
            "allowed_actions": ["watch"],
            "invalid_if": [],
            "risk_management": {"max_position_size_pct": 0.0, "stop_loss_pct": None, "notes": "Do not initiate new buys."},
        },
        "watch_only": {
            "label": "watch_only",
            "allowed_actions": ["watch"],
            "invalid_if": [],
            "risk_management": {"max_position_size_pct": None, "stop_loss_pct": None, "notes": "Build watchlist only."},
        },
        "low_priority": {
            "label": "low_priority",
            "allowed_actions": ["watch"],
            "invalid_if": [],
            "risk_management": {"max_position_size_pct": None, "stop_loss_pct": None, "notes": "Low priority candidate."},
        },
        "risk_warning": {
            "label": "risk_warning",
            "allowed_actions": ["watch"],
            "invalid_if": [],
            "risk_management": {"max_position_size_pct": 0.0, "stop_loss_pct": None, "notes": "Elevated risk flags present."},
        },
    }
    return plans.get(label, plans["low_priority"])


def determine_final_label(
    market_status: str,
    technical_score: float,
    rs_score: float | None,
    is_breakout: bool,
    has_warning: bool,
    llm_safe: bool,
) -> tuple[str, str]:
    if not llm_safe:
        return "data_not_safe", rc.UNSAFE_LLM_INSTRUCTION

    rs_threshold = 70.0

    if market_status == "Market in Correction":
        return "watch_only", "Market in correction — watch only, no new buys."

    if has_warning:
        return "risk_warning", "Warning flags present — reduce priority and manage risk."

    if market_status == "Confirmed Uptrend" and is_breakout and rs_score is not None and rs_score >= rs_threshold:
        return "breakout_watch", "Strong breakout with RS — watch for confirmed entry timing."

    if market_status == "Confirmed Uptrend" and technical_score >= 75 and rs_score is not None and rs_score >= rs_threshold:
        return "watch_for_setup", "Strong technical profile but no timing signal — watch for setup."

    if market_status in ("Rally Attempt", "Uptrend Under Pressure"):
        return "watch_for_setup", "Market not fully confirmed — watch for setup only."

    return "low_priority", "Monitor stock; insufficient signals for higher priority."
