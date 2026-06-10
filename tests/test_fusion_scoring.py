from __future__ import annotations

import pandas as pd
import pytest

from src.fusion.reason_codes import DATA_NOT_SAFE_FOR_LLM, UNSAFE_LLM_INSTRUCTION, UNSAFE_NEGATIVE_REASON
from src.fusion.rules import unsafe_composite_snapshot
from src.fusion.scoring import build_stock_snapshot, compute_composite_snapshot


@pytest.fixture
def strong_row() -> pd.Series:
    return pd.Series(
        {
            "ticker": "FPT",
            "sector": "Technology",
            "close": 100.0,
            "change_pct": 2.0,
            "volume_ratio": 1.8,
            "rs_score": 85,
            "above_ma50": True,
            "above_ma200": True,
            "distance_from_52w_high_pct": -5.0,
            "breakout": True,
            "break_ma50": False,
            "warning": False,
        }
    )


@pytest.fixture
def cfg() -> dict:
    return {"fusion": {"weights": {"market": 0.25, "technical": 0.35}}}


def test_unsafe_composite_contract():
    comp = unsafe_composite_snapshot()
    assert comp.final_label == "data_not_safe"
    assert comp.llm_instruction == UNSAFE_LLM_INSTRUCTION
    assert comp.final_score == 0
    assert comp.positive_reasons == []
    assert UNSAFE_NEGATIVE_REASON in comp.negative_reasons
    assert DATA_NOT_SAFE_FOR_LLM in comp.reason_codes


def test_unsafe_short_circuit_on_stock(strong_row, cfg):
    snap = build_stock_snapshot(strong_row, "Confirmed Uptrend", llm_safe=False, cfg=cfg)
    assert snap.composite.final_label == "data_not_safe"
    assert snap.composite.llm_instruction == UNSAFE_LLM_INSTRUCTION
    assert snap.composite.final_score == 0
    assert snap.composite.positive_reasons == []
    assert DATA_NOT_SAFE_FOR_LLM in snap.composite.reason_codes


def test_correction_no_actionable(strong_row, cfg):
    comp = compute_composite_snapshot(strong_row, "Market in Correction", llm_safe=True, cfg=cfg)
    assert comp.final_label != "actionable_candidate"
    assert comp.final_label == "watch_only"


def test_confirmed_uptrend_strong_no_timing_watch_setup(strong_row, cfg):
    comp = compute_composite_snapshot(strong_row, "Confirmed Uptrend", llm_safe=True, cfg=cfg)
    assert comp.final_label in ("breakout_watch", "watch_for_setup")
    assert comp.final_label != "actionable_candidate"


def test_demo_data_not_safe_via_build(strong_row, cfg):
    comp = compute_composite_snapshot(strong_row, "Confirmed Uptrend", llm_safe=False, cfg=cfg)
    assert comp.final_label == "data_not_safe"
