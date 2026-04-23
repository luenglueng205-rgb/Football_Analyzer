from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, TypedDict


class ProviderError(TypedDict, total=False):
    code: str
    message: str


class ProviderMeta(TypedDict, total=False):
    source: str
    mock: bool
    confidence: float
    stale: bool
    raw_ref: str
    degradations: list[str]


class ProviderResponse(TypedDict, total=False):
    ok: bool
    data: Any
    error: Optional[ProviderError]
    meta: ProviderMeta


class DataProvider(Protocol):
    def fetch(self, **kwargs: Any) -> ProviderResponse: ...

    def name(self) -> str: ...
