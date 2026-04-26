from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar


T = TypeVar("T")


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}


def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return float(str(v).strip())
    except Exception:
        return default


@dataclass(frozen=True)
class NetworkPolicy:
    online: bool
    ddgs_timeout_s: float

    @staticmethod
    def from_env(*, online: Optional[bool] = None) -> "NetworkPolicy":
        resolved_online = bool(online) if online is not None else _env_bool("DATA_FABRIC_ONLINE", False)
        ddgs_timeout_s = _env_float("AGENT_BROWSER_DDGS_TIMEOUT_S", 4.0)
        if ddgs_timeout_s <= 0:
            ddgs_timeout_s = 0.1
        return NetworkPolicy(online=resolved_online, ddgs_timeout_s=ddgs_timeout_s)


class NetworkGatekeeper:
    def __init__(self, *, policy: Optional[NetworkPolicy] = None, online: Optional[bool] = None):
        self.policy = policy or NetworkPolicy.from_env(online=online)

    def allow_network(self) -> bool:
        return bool(self.policy.online)

    def run_sync(self, fn: Callable[[], T], *, timeout_s: float, default: T) -> T:
        if timeout_s <= 0:
            timeout_s = 0.1

        out: T = default
        err: Exception | None = None

        def runner():
            nonlocal out, err
            try:
                out = fn()
            except Exception as e:
                err = e

        t = threading.Thread(target=runner, daemon=True)
        t.start()
        t.join(timeout=timeout_s)
        if t.is_alive():
            return default
        if err is not None:
            return default
        return out
