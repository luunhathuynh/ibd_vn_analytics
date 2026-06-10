from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse

from src.api.deps import SERVICE_VERSION, get_config
from src.api.report_store import (
    RealDataUnavailableError,
    ReportNotFoundError,
    load_data_status_from_cache,
    load_or_generate_report,
    load_report_cached,
    no_cached_report_response,
    real_data_unavailable_response,
)
from src.data.data_status import empty_unsafe_data_status
from src.pipeline import create_provider_with_info
from src.schemas.llm import CandidatesResponse, DailyMarketReportJson, DataStatus, ExplainResponse

app = FastAPI(title="ibd_vn_analytics", version=SERVICE_VERSION)


def _optional_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    cfg: dict = Depends(get_config),
) -> None:
    api_cfg = cfg.get("api", {})
    if not api_cfg.get("auth_enabled", False):
        return
    expected = os.getenv(api_cfg.get("api_key_env", "IBD_API_KEY"), "")
    if not expected or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ibd_vn_analytics", "version": SERVICE_VERSION}


@app.get("/api/v1/data-status", response_model=DataStatus, dependencies=[Depends(_optional_api_key)])
def data_status(
    probe: bool = Query(default=False),
    cfg: dict = Depends(get_config),
) -> DataStatus:
    if probe:
        _, info = create_provider_with_info(cfg.get("provider"))
        status = load_data_status_from_cache()
        if info.init_fallback or info.demo_requested:
            return empty_unsafe_data_status("Provider probe indicates demo or fallback data.")
        return status
    return load_data_status_from_cache()


@app.get(
    "/api/v1/market/daily",
    response_model=DailyMarketReportJson,
    responses={503: {"description": "No cache or real data unavailable"}},
    dependencies=[Depends(_optional_api_key)],
)
def market_daily(
    date: str = Query(default="latest"),
    refresh: bool = Query(default=False),
    allow_stale: bool = Query(default=False),
    cfg: dict = Depends(get_config),
):
    if not refresh:
        try:
            return load_report_cached(date)
        except ReportNotFoundError:
            body = no_cached_report_response()
            return JSONResponse(status_code=503, content=body.model_dump())

    try:
        return load_or_generate_report(date, refresh=True, allow_stale=allow_stale, for_api=True, cfg=cfg)
    except RealDataUnavailableError as exc:
        body = real_data_unavailable_response(str(exc), exc.data_status)
        return JSONResponse(status_code=503, content=body.model_dump())


@app.get("/api/v1/candidates", dependencies=[Depends(_optional_api_key)])
def candidates(
    date: str = Query(default="latest"),
    refresh: bool = Query(default=False),
    allow_stale: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    cfg: dict = Depends(get_config),
):
    if not refresh:
        try:
            report = load_report_cached(date)
        except ReportNotFoundError:
            body = no_cached_report_response()
            return JSONResponse(status_code=503, content=body.model_dump())
    else:
        try:
            report = load_or_generate_report(date, refresh=True, allow_stale=allow_stale, for_api=True, cfg=cfg)
        except RealDataUnavailableError as exc:
            body = real_data_unavailable_response(str(exc), exc.data_status)
            return JSONResponse(status_code=503, content=body.model_dump())

    return CandidatesResponse(
        report_date=report.report_date,
        generated_at=report.generated_at,
        data_status=report.data_status,
        market_context=report.market_context,
        candidates=report.top_candidates[:limit],
    )


def _find_stock(report: DailyMarketReportJson, symbol: str):
    sym = symbol.upper()
    for group in (
        report.top_candidates,
        report.leaders,
        report.breakouts,
        report.watchlist,
        report.warnings,
    ):
        for snap in group:
            if snap.symbol.upper() == sym:
                return snap
    return None


@app.get("/api/v1/stocks/{symbol}/snapshot", dependencies=[Depends(_optional_api_key)])
def stock_snapshot(
    symbol: str,
    date: str = Query(default="latest"),
    refresh: bool = Query(default=False),
    allow_stale: bool = Query(default=False),
    cfg: dict = Depends(get_config),
):
    if not refresh:
        try:
            report = load_report_cached(date)
        except ReportNotFoundError:
            body = no_cached_report_response()
            return JSONResponse(status_code=503, content=body.model_dump())
    else:
        try:
            report = load_or_generate_report(date, refresh=True, allow_stale=allow_stale, for_api=True, cfg=cfg)
        except RealDataUnavailableError as exc:
            body = real_data_unavailable_response(str(exc), exc.data_status)
            return JSONResponse(status_code=503, content=body.model_dump())

    snap = _find_stock(report, symbol)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol.upper()} not found in report.")
    return snap


@app.get("/api/v1/stocks/{symbol}/explain", response_model=ExplainResponse, dependencies=[Depends(_optional_api_key)])
def explain_symbol(
    symbol: str,
    date: str = Query(default="latest"),
    refresh: bool = Query(default=False),
    allow_stale: bool = Query(default=False),
    cfg: dict = Depends(get_config),
):
    if not refresh:
        try:
            report = load_report_cached(date)
        except ReportNotFoundError:
            body = no_cached_report_response()
            return JSONResponse(status_code=503, content=body.model_dump())
    else:
        try:
            report = load_or_generate_report(date, refresh=True, allow_stale=allow_stale, for_api=True, cfg=cfg)
        except RealDataUnavailableError as exc:
            body = real_data_unavailable_response(str(exc), exc.data_status)
            return JSONResponse(status_code=503, content=body.model_dump())

    snap = _find_stock(report, symbol)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol.upper()} not found in report.")

    return ExplainResponse(
        symbol=snap.symbol,
        report_date=report.report_date,
        final_label=snap.composite.final_label,
        positive_reasons=snap.composite.positive_reasons,
        negative_reasons=snap.composite.negative_reasons,
        reason_codes=snap.composite.reason_codes,
        llm_instruction=snap.composite.llm_instruction,
    )
