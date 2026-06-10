from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from src.schemas.llm import DataStatus


class ErrorCode(StrEnum):
    NO_CACHED_REPORT = "NO_CACHED_REPORT"
    REAL_DATA_UNAVAILABLE = "REAL_DATA_UNAVAILABLE"


class ApiError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ApiErrorResponse(BaseModel):
    error: ApiError
    data_status: DataStatus | None = None

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        return super().model_dump(mode="json", **kwargs)
