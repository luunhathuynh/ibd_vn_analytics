from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from src.config import load_config
from src.data.data_status import empty_unsafe_data_status
from src.data.models import DataUnavailableError
from src.pipeline import run_pipeline
from src.report.json_report import load_report_from_file
from src.schemas.errors import ApiError, ApiErrorResponse, ErrorCode
from src.schemas.llm import DailyMarketReportJson, DataStatus


REPORT_JSON_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})_market_report\.json$")


class ReportNotFoundError(Exception):
    pass


class RealDataUnavailableError(Exception):
    def __init__(self, message: str, data_status: DataStatus | None = None) -> None:
        super().__init__(message)
        self.data_status = data_status


def reports_dir(cfg: dict | None = None) -> Path:
    _ = cfg
    return Path("reports")


def find_latest_cached_report(base: Path | None = None) -> Path | None:
    directory = base or reports_dir()
    if not directory.exists():
        return None
    candidates = sorted(directory.glob("*_market_report.json"), reverse=True)
    return candidates[0] if candidates else None


def report_path_for_date(report_date: date, base: Path | None = None) -> Path:
    directory = base or reports_dir()
    return directory / f"{report_date.isoformat()}_market_report.json"


def load_data_status_from_cache(base: Path | None = None) -> DataStatus:
    path = find_latest_cached_report(base)
    if path is None:
        return empty_unsafe_data_status()
    report = load_report_from_file(path)
    return report.data_status


def load_report_cached(
    date_param: str,
    *,
    base: Path | None = None,
) -> DailyMarketReportJson:
    directory = base or reports_dir()
    if date_param == "latest":
        path = find_latest_cached_report(directory)
    else:
        path = report_path_for_date(date.fromisoformat(date_param), directory)
        if not path.exists():
            path = None  # type: ignore[assignment]

    if path is None or not path.exists():
        raise ReportNotFoundError(f"No cached report for date={date_param}")

    report = load_report_from_file(path)
    if date_param == "latest":
        report.data_status.is_stale = True
        if "Served from cache" not in " ".join(report.data_status.warnings):
            report.data_status.warnings.append("Served from cache; use refresh=true for latest session.")
    return report


def load_or_generate_report(
    date_param: str,
    *,
    refresh: bool = False,
    allow_stale: bool = False,
    for_api: bool = True,
    base: Path | None = None,
    cfg: dict | None = None,
) -> DailyMarketReportJson:
    config = cfg or load_config()
    directory = base or reports_dir()

    if not refresh:
        try:
            return load_report_cached(date_param, base=directory)
        except ReportNotFoundError:
            raise

    latest = date_param == "latest"
    requested = date.today() if latest else date.fromisoformat(date_param)
    allow_demo = not for_api or config.get("provider", {}).get("allow_demo_fallback_for_api", False)

    try:
        result = run_pipeline(
            requested,
            config,
            latest=latest,
            allow_demo_fallback=allow_demo,
            write_outputs=True,
            reports_dir=directory,
        )
        json_path = directory / f"{result.metadata.report_date.isoformat()}_market_report.json"
        return load_report_from_file(json_path)
    except (DataUnavailableError, ReportNotFoundError) as exc:
        if allow_stale:
            try:
                report = load_report_cached(date_param, base=directory)
                report.data_status.is_stale = True
                report.data_status.warnings.append(f"Refresh failed: {exc}")
                report.data_status.llm_safe_to_analyze = False
                return report
            except ReportNotFoundError:
                pass
        status = empty_unsafe_data_status(str(exc))
        raise RealDataUnavailableError(str(exc), data_status=status) from exc


def no_cached_report_response() -> ApiErrorResponse:
    status = empty_unsafe_data_status("No cached JSON report available.")
    status.errors.append(ErrorCode.NO_CACHED_REPORT)
    return ApiErrorResponse(
        error=ApiError(
            code=ErrorCode.NO_CACHED_REPORT,
            message="No cached market report available. Use refresh=true to generate a new report.",
            retryable=True,
        ),
        data_status=status,
    )


def real_data_unavailable_response(message: str, data_status: DataStatus | None = None) -> ApiErrorResponse:
    status = data_status or empty_unsafe_data_status(message)
    return ApiErrorResponse(
        error=ApiError(
            code=ErrorCode.REAL_DATA_UNAVAILABLE,
            message=message,
            retryable=True,
        ),
        data_status=status,
    )
