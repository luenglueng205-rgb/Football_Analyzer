import json
import os
import select
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, TextIO


class AssertionFailed(RuntimeError):
    pass


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionFailed(msg)


def _readline_with_timeout(stream: TextIO, timeout_s: float) -> str:
    end_at = time.time() + timeout_s
    while True:
        remaining = end_at - time.time()
        if remaining <= 0:
            raise TimeoutError("Timed out waiting for response from mcp_server")
        readable, _, _ = select.select([stream], [], [], remaining)
        if not readable:
            continue
        line = stream.readline()
        if not line:
            raise EOFError("mcp_server stdout closed unexpectedly")
        line = line.strip()
        if line:
            return line


@dataclass
class RpcServer:
    proc: subprocess.Popen
    next_id: int = 1

    def call(self, method: str, params: Optional[Dict[str, Any]] = None, timeout_s: float = 30.0) -> Dict[str, Any]:
        req: Dict[str, Any] = {"id": self.next_id, "method": method}
        self.next_id += 1
        if params is not None:
            req["params"] = params
        payload = json.dumps(req, ensure_ascii=False)
        _assert(self.proc.stdin is not None, "mcp_server stdin unavailable")
        self.proc.stdin.write(payload + "\n")
        self.proc.stdin.flush()

        _assert(self.proc.stdout is not None, "mcp_server stdout unavailable")
        line = _readline_with_timeout(self.proc.stdout, timeout_s=timeout_s)
        res = json.loads(line)
        _assert(res.get("id") == req["id"], f"rpc id mismatch: req={req['id']} res={res.get('id')}")
        return res

    def terminate(self) -> None:
        if self.proc.poll() is not None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=3)


def _start_server(workspace_root: Path) -> RpcServer:
    env = os.environ.copy()
    env.setdefault("OPENAI_API_KEY", "dummy-key-for-test")
    env.setdefault("OPENAI_API_BASE", "http://127.0.0.1:1/v1")
    env.setdefault("OPENAI_MODEL", "gpt-4o-mini")
    env.setdefault("OPENCLAW_MOCK_LLM", "1")
    env.setdefault("OPENCLAW_DAEMON_MODE", "noop")
    env.setdefault("ANALYZER_API_URL", "http://127.0.0.1:1")

    proc = subprocess.Popen(
        [sys.executable, "src/mcp_server.py"],
        cwd=str(workspace_root),
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    return RpcServer(proc=proc)


def _extract_workflow_payload(res: Dict[str, Any]) -> Dict[str, Any]:
    _assert("error" not in res, f"rpc error: {res.get('error')}")
    payload = res.get("result")
    _assert(isinstance(payload, dict), f"workflow result is not a dict: {type(payload)}")
    return payload


def _find_keys(payload: Dict[str, Any]) -> Dict[str, Any]:
    if {"scout_report", "debates", "final_decision", "publisher_report_path"}.issubset(payload.keys()):
        return payload

    data = payload.get("data")
    if isinstance(data, dict) and {"scout_report", "debates", "final_decision", "publisher_report_path"}.issubset(data.keys()):
        return data

    os_result = None
    if isinstance(data, dict):
        os_result = data.get("os_result")
    if os_result is None:
        os_result = payload.get("os_result")

    if isinstance(os_result, dict):
        merged = dict(os_result)
        if isinstance(data, dict) and "publisher_report_path" in data:
            merged["publisher_report_path"] = data.get("publisher_report_path")
        if "publisher_report_path" in payload:
            merged["publisher_report_path"] = payload.get("publisher_report_path")
        return merged

    return payload


def main() -> None:
    workspace_root = Path(__file__).resolve().parents[1]
    server = _start_server(workspace_root)
    try:
        list_res = server.call("list_tools", timeout_s=30.0)
        tools = list_res.get("tools") or []
        _assert(isinstance(tools, list), f"list_tools.tools is not a list: {type(tools)}")
        tool_names = {t.get("name") for t in tools if isinstance(t, dict)}
        required = {"calculate_all_markets", "retrieve_team_memory", "save_team_insight"}
        missing = sorted(required - tool_names)
        _assert(not missing, f"list_tools missing tools: {missing}")

        wf_res = server.call(
            "run_workflow",
            params={"name": "run_once_match", "arguments": {"home_team": "曼城", "away_team": "阿森纳", "lottery_desc": "竞彩足球"}},
            timeout_s=120.0,
        )
        payload = _extract_workflow_payload(wf_res)
        fields = _find_keys(payload)
        for k in ["scout_report", "debates", "final_decision", "publisher_report_path"]:
            _assert(k in fields, f"run_once_match missing field: {k}")

        status_0 = _extract_workflow_payload(server.call("daemon_status", timeout_s=10.0))
        _assert(status_0.get("ok") is True, f"daemon_status failed: {status_0}")
        _assert(status_0.get("data", {}).get("running") is False, f"daemon_status expected running=false: {status_0}")

        start = _extract_workflow_payload(
            server.call("daemon_start", params={"arguments": {"max_workers": 1, "polling_interval": 3600}}, timeout_s=10.0)
        )
        _assert(start.get("ok") is True, f"daemon_start failed: {start}")
        _assert(start.get("data", {}).get("running") is True, f"daemon_start expected running=true: {start}")

        status_1 = _extract_workflow_payload(server.call("daemon_status", timeout_s=10.0))
        _assert(status_1.get("ok") is True, f"daemon_status failed: {status_1}")
        _assert(status_1.get("data", {}).get("running") is True, f"daemon_status expected running=true: {status_1}")

        stop = _extract_workflow_payload(server.call("daemon_stop", timeout_s=20.0))
        _assert(stop.get("ok") is True, f"daemon_stop failed: {stop}")
        _assert(stop.get("data", {}).get("running") is False, f"daemon_stop expected running=false: {stop}")

        status_2 = _extract_workflow_payload(server.call("daemon_status", timeout_s=10.0))
        _assert(status_2.get("ok") is True, f"daemon_status failed: {status_2}")
        _assert(status_2.get("data", {}).get("running") is False, f"daemon_status expected running=false: {status_2}")

        print("Task6 acceptance test: OK")
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
