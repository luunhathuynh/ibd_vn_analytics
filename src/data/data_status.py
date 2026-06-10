from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.fusion import reason_codes as rc
from src.pipeline_models import PipelineMetadata
from src.schemas.llm import DataStatus


def build_data_status(
    metadata: PipelineMetadata,
    cfg: dict[str, Any],
    *,
    is_stale: bool = False,
    generated_at: str | None = None,
) -> DataStatus:
    provider_cfg = cfg.get("provider", {})
    min_ratio = float(provider_cfg.get("min_real_stock_success_ratio", 0.8))
    warnings = list(metadata.warnings)
    errors: list[str] = []

    is_demo = metadata.is_demo
    is_real = not is_demo and not metadata.fallback_used
    llm_safe = is_real

    if metadata.demo_requested:
        warnings.append("Demo data only. Do not use for real market analysis.")
        errors.append(rc.DATA_DEMO_PROVIDER)
        llm_safe = False
        is_real = False
    elif metadata.fallback_used:
        warnings.append("Demo data only. Do not use for real market analysis.")
        warnings.append("VNStockProvider failed and demo fallback was used.")
        errors.append(rc.DATA_FALLBACK_USED)
        llm_safe = False
        is_real = False
    elif is_demo:
        warnings.append("Demo data only. Do not use for real market analysis.")
        errors.append(rc.DATA_DEMO_PROVIDER)
        llm_safe = False
        is_real = False
    else:
        warnings.append(rc.DATA_REAL_PROVIDER)
        attempted = len(metadata.attempted_symbols)
        succeeded = len(metadata.succeeded_symbols)
        ratio = (succeeded / attempted) if attempted else 0.0
        if attempted == 0 or ratio < min_ratio:
            llm_safe = False
            errors.append(
                f"Real data success ratio {ratio:.0%} below threshold {min_ratio:.0%}."
            )
            warnings.append("Insufficient real stock data for LLM analysis.")

    if is_stale:
        warnings.append("Report data is stale — not refreshed for latest session.")

    if not llm_safe:
        errors.append(rc.DATA_NOT_SAFE_FOR_LLM)

    last_update = generated_at or datetime.now(timezone.utc).isoformat()

    return DataStatus(
        provider=metadata.provider_name,
        is_real_data=is_real,
        fallback_used=metadata.fallback_used,
        llm_safe_to_analyze=llm_safe,
        last_successful_update=last_update if llm_safe else None,
        report_date=metadata.report_date.isoformat(),
        missing_symbols=list(metadata.missing_symbols),
        failed_symbols=list(metadata.failed_symbols),
        warnings=warnings,
        errors=errors,
        is_stale=is_stale,
        generated_at=generated_at,
    )


def empty_unsafe_data_status(message: str = "No cached JSON report available.") -> DataStatus:
    return DataStatus(
        provider="unknown",
        is_real_data=False,
        fallback_used=False,
        llm_safe_to_analyze=False,
        warnings=[message],
        errors=[rc.DATA_NOT_SAFE_FOR_LLM],
    )
