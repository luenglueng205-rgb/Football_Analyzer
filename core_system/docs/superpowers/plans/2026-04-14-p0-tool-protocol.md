# P0 - 1. Tool Return Protocol Unification

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unify tool returns to `{ "ok": bool, "data": Any, "error": dict|null, "meta": dict }` and ban silent `{}` returns.

**Architecture:** Modify `mcp_tools.py` wrapper functions. Instead of returning raw dicts or empty dicts on failure, wrap the result in the standard protocol. Use an `ensure_protocol` decorator to catch exceptions and return structured errors.

**Tech Stack:** Python 3.

---

### Task 1: Create Protocol Decorator

**Files:**
- Modify: `tools/mcp_tools.py:1-60`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from tools.mcp_tools import get_team_stats

def test_protocol():
    res = get_team_stats("UnknownTeam")
    assert "ok" in res
    assert "meta" in res
```

- [ ] **Step 2: Write minimal implementation**

Add the decorator in `tools/mcp_tools.py` before the functions.

```python
import functools
import inspect

def ensure_protocol(mock=False, source="local"):
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                res = await func(*args, **kwargs)
                if isinstance(res, dict) and "ok" in res and "meta" in res:
                    return res
                return {"ok": True, "data": res, "error": None, "meta": {"mock": mock, "source": source}}
            except Exception as e:
                logger.error(f"Tool {func.__name__} failed: {e}")
                return {"ok": False, "data": None, "error": {"code": "EXECUTION_ERROR", "message": str(e)}, "meta": {"mock": mock, "source": source}}
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                res = func(*args, **kwargs)
                if isinstance(res, dict) and "ok" in res and "meta" in res:
                    return res
                return {"ok": True, "data": res, "error": None, "meta": {"mock": mock, "source": source}}
            except Exception as e:
                logger.error(f"Tool {func.__name__} failed: {e}")
                return {"ok": False, "data": None, "error": {"code": "EXECUTION_ERROR", "message": str(e)}, "meta": {"mock": mock, "source": source}}
                
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
```

- [ ] **Step 3: Apply decorator to all tools in `mcp_tools.py`**
Remove all `try...except` blocks inside the wrapper functions in `mcp_tools.py` and let the decorator handle it.

Example:
```python
@ensure_protocol(mock=False, source="parlay_matrix")
def calculate_parlay(matches: list, parlay_type: str, total_stake: float) -> dict:
    return _parlay_matrix.calculate_parlay(matches, parlay_type, total_stake)
```
Do this for all functions mapped in `TOOL_MAPPING`.

- [ ] **Step 4: Commit**
Run: `git commit -am "feat: enforce standard tool return protocol"`
