from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProviderCreationInfo:
    demo_requested: bool
    init_fallback: bool


@dataclass
class PipelineMetadata:
    provider_name: str
    is_demo: bool
    demo_requested: bool
    fallback_used: bool
    report_date: date
    requested_date: date
    attempted_symbols: list[str] = field(default_factory=list)
    succeeded_symbols: list[str] = field(default_factory=list)
    failed_symbols: list[str] = field(default_factory=list)
    missing_symbols: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    payload: dict[str, Any]
    metadata: PipelineMetadata
    md_path: Path | None = None
