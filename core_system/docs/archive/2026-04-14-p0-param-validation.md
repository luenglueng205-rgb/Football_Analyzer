# P0 - 5. Parameter strong validation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Catch tool argument parsing failures explicitly and return standard error to LLM.

**Architecture:** Modify `agents/ai_native_core.py` to correctly parse parameters. If `json.loads(tool_call.function.arguments)` fails, return `{"ok": False, "error": {"code": "BAD_ARGS", "message": "Failed to parse arguments as JSON."}}` directly instead of falling back to `{}`.

**Tech Stack:** Python 3.

---

### Task 1: Update Parameter Parsing

**Files:**
- Modify: `agents/ai_native_core.py:120-160`

- [ ] **Step 1: Write implementation**

Find the `json.loads` part in `agents/ai_native_core.py`:
```python
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except Exception:
                        arguments = {}
```

Replace with:
```python
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except Exception as e:
                        logger.error(f"Failed to parse tool arguments for {function_name}: {e}")
                        error_msg = {"ok": False, "error": {"code": "BAD_ARGS", "message": f"Failed to parse arguments as JSON: {str(e)}"}, "meta": {"mock": False}}
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": str(error_msg)
                        })
                        continue
```

- [ ] **Step 2: Commit**
Run: `git commit -am "fix: prevent silent fallback to empty dict on arg parse failure"`
