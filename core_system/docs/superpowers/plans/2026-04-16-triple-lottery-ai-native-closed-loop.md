# 体彩三彩种 AI 原生闭环（竞彩/北单/足彩）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在独立版与 OpenClaw 适配版中，实现中国体育彩票三彩种（竞彩足球/北京单场/传统足彩）的“推荐→出票校验→模拟执行→临场→结算→复盘”闭环，并把 22 万历史数据影响以 `historical_impact`（顶层摘要）+ `audit.explain`（证据链）统一输出。

**Architecture:** 采用“彩种专属 Workflow + 共享公共组件”的结构：JINGCAI/BEIDAN/ZUCAI 各自 workflow 负责数据与玩法差异；共用 TicketBuilder/Router/Parlay/Settlement/Ledger/Reporter/Memory/历史影响证据链输出。

**Tech Stack:** Python, pytest, ChromaDB, SnapshotStore, （可选在线）WebIntel/BrowserUse；默认离线不联网。

---

## File Map（本计划涉及文件）

**Standalone（源码真相源）**
- Modify: `standalone_workspace/core/mentor_workflow.py`（JINGCAI 已有，保持；补离线开关与历史证据链一致性）
- Create: `standalone_workspace/core/beidan_workflow.py`
- Create: `standalone_workspace/core/zucai_workflow.py`
- Modify: `standalone_workspace/tools/ticket_builder.py`（支持 8/15/14 legs 与 ZUCAI play_type）
- Modify: `standalone_workspace/scripts/mentor_cli.py`（新增 --lottery-type / --zucai-play-type / --online）
- Create: `standalone_workspace/tools/historical_impact.py`（统一构建 historical_impact + explain item）
- Modify: `standalone_workspace/tools/multisource_fetcher.py`（默认离线不走 web_intel/foreign，online 才启用）
- Tests:
  - Modify: `standalone_workspace/tests/test_mentor_cli.py`
  - Create: `standalone_workspace/tests/test_beidan_workflow.py`
  - Create: `standalone_workspace/tests/test_zucai_workflow.py`
  - Modify: `standalone_workspace/tests/test_closed_loop_trade.py`（覆盖三彩种闭环）

**OpenClaw Runtime（适配版）**
- Modify: `openclaw_workspace/runtime/football_analyzer/tools/mentor_tools.py`（为 BEIDAN/ZUCAI 增加入口或参数；输出 historical_impact）
- Modify: `openclaw_workspace/runtime/football_analyzer/tests/test_mcp_mentor_tools.py`

---

## Task 1: 抽象 Historical Impact（统一摘要 + 证据链）

**Files:**
- Create: `standalone_workspace/tools/historical_impact.py`
- Modify: `standalone_workspace/core/mentor_workflow.py`
- Test: `standalone_workspace/tests/test_historical_impact.py`

- [ ] **Step 1: 写 failing test（historical_impact schema 与 explain item）**

```python
import pytest

from tools.historical_impact import build_historical_impact, to_explain_item


def test_historical_impact_schema_has_required_keys():
    hi = build_historical_impact(
        lottery_type="JINGCAI",
        league_code="E0",
        odds={"home": 2.1, "draw": 3.4, "away": 3.2},
        analysis={
            "calibration_info": {"calibrated": True, "historical_weight": 0.25, "sample_size": 1000, "hist_distribution": {"home": 0.45, "draw": 0.26, "away": 0.29}},
            "league_stats": {"avg_goals": 2.7, "over_2_5_rate": 0.52, "btts_rate": 0.47, "draw_rate": 0.26, "sample_size": 1000},
        },
        similar_odds_result={"ok": True, "data": []},
        data_source={"raw_json_path": "x", "chroma_db_path": "y"},
    )
    assert hi["enabled"] is True
    assert hi["lottery_type"] == "JINGCAI"
    assert "league_stats" in hi
    assert "market_calibration" in hi
    assert "similar_odds" in hi
    assert "data_source" in hi
    assert isinstance(hi["degradations"], list)


def test_historical_explain_item_contains_summary_and_samples():
    hi = build_historical_impact(
        lottery_type="ZUCAI",
        league_code="E0",
        odds=None,
        analysis={},
        similar_odds_result=None,
        data_source={"raw_json_path": "x", "chroma_db_path": "y"},
    )
    item = to_explain_item(hi)
    assert item["type"] == "historical_impact"
    assert "summary" in item
    assert "samples" in item
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest -q standalone_workspace/tests/test_historical_impact.py
```

Expected: FAIL（找不到模块/函数）。

- [ ] **Step 3: 实现最小 build_historical_impact / to_explain_item**

```python
from __future__ import annotations

from typing import Any, Dict, Optional

from tools.paths import datasets_dir


def build_historical_impact(
    *,
    lottery_type: str,
    league_code: str,
    odds: Optional[Dict[str, float]],
    analysis: Dict[str, Any],
    similar_odds_result: Optional[Dict[str, Any]] = None,
    data_source: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "enabled": True,
        "lottery_type": str(lottery_type).upper(),
        "league_code": str(league_code or "UNK"),
        "league_stats": None,
        "market_calibration": {"enabled": False, "method": "league_distribution_blend", "historical_weight": None, "calibrated": False},
        "similar_odds": {"enabled": False, "tolerance": 0.10, "matched_count": 0, "sample": []},
        "data_source": data_source
        or {
            "raw_json_path": datasets_dir("raw", "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json"),
            "chroma_db_path": None,
        },
        "degradations": [],
    }

    cal = analysis.get("calibration_info") if isinstance(analysis.get("calibration_info"), dict) else {}
    hist = cal.get("hist_distribution") if isinstance(cal.get("hist_distribution"), dict) else {}
    ls = analysis.get("league_stats") if isinstance(analysis.get("league_stats"), dict) else {}
    sample_size = cal.get("sample_size") if isinstance(cal.get("sample_size"), int) else ls.get("sample_size")
    out["league_stats"] = {
        "sample_size": int(sample_size) if isinstance(sample_size, (int, float)) else 0,
        "home_win_rate": float(hist.get("home")) if isinstance(hist.get("home"), (int, float)) else None,
        "draw_rate": float(ls.get("draw_rate")) if isinstance(ls.get("draw_rate"), (int, float)) else (float(hist.get("draw")) if isinstance(hist.get("draw"), (int, float)) else None),
        "away_win_rate": float(hist.get("away")) if isinstance(hist.get("away"), (int, float)) else None,
        "avg_total_goals": float(ls.get("avg_goals")) if isinstance(ls.get("avg_goals"), (int, float)) else None,
        "over_2_5_rate": float(ls.get("over_2_5_rate")) if isinstance(ls.get("over_2_5_rate"), (int, float)) else None,
        "btts_yes_rate": float(ls.get("btts_rate")) if isinstance(ls.get("btts_rate"), (int, float)) else None,
    }

    calibrated = bool(cal.get("calibrated")) if isinstance(cal, dict) else False
    if cal:
        out["market_calibration"] = {
            "enabled": True,
            "method": "league_distribution_blend",
            "historical_weight": cal.get("historical_weight"),
            "calibrated": calibrated,
        }

    if isinstance(out["league_stats"].get("sample_size"), int) and out["league_stats"]["sample_size"] <= 0:
        out["degradations"].append("league_stats_unavailable")

    if not calibrated and isinstance(cal.get("reason"), str) and cal.get("reason"):
        out["degradations"].append(f"market_calibration:{cal.get('reason')}")

    if out["lottery_type"] == "ZUCAI":
        out["similar_odds"]["enabled"] = False
        out["degradations"].append("similar_odds_not_applicable:zucai_no_fixed_odds")
        return out

    if odds is None:
        out["degradations"].append("odds_unavailable")
        return out

    if isinstance(similar_odds_result, dict) and similar_odds_result.get("ok") is True and isinstance(similar_odds_result.get("data"), list):
        sample = []
        for item in similar_odds_result["data"][:3]:
            meta = item.get("metadata") if isinstance(item, dict) else None
            meta = meta if isinstance(meta, dict) else {}
            sample.append(
                {
                    "match_id": meta.get("match_id") or meta.get("id") or None,
                    "date": meta.get("date"),
                    "result": meta.get("result"),
                    "home_team": meta.get("home_team"),
                    "away_team": meta.get("away_team"),
                    "home_odds": meta.get("home_odds"),
                    "draw_odds": meta.get("draw_odds"),
                    "away_odds": meta.get("away_odds"),
                }
            )
        out["similar_odds"] = {"enabled": True, "tolerance": 0.10, "matched_count": len(similar_odds_result["data"]), "sample": sample}
        if not similar_odds_result["data"]:
            out["degradations"].append("similar_odds_unavailable")
    else:
        out["degradations"].append("similar_odds_unavailable")
    return out


def to_explain_item(historical_impact: Dict[str, Any]) -> Dict[str, Any]:
    sim = historical_impact.get("similar_odds") if isinstance(historical_impact.get("similar_odds"), dict) else {}
    return {
        "type": "historical_impact",
        "summary": {
            "enabled": historical_impact.get("enabled"),
            "lottery_type": historical_impact.get("lottery_type"),
            "league_code": historical_impact.get("league_code"),
            "league_stats": historical_impact.get("league_stats"),
            "market_calibration": historical_impact.get("market_calibration"),
            "similar_odds": {k: v for k, v in sim.items() if k != "sample"},
            "data_source": historical_impact.get("data_source"),
            "degradations": historical_impact.get("degradations"),
        },
        "samples": sim.get("sample", []),
    }
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest -q standalone_workspace/tests/test_historical_impact.py
```

Expected: PASS。

- [ ] **Step 5: 将 MentorWorkflow 的 historical_impact 计算迁移为调用上述工具**

目标：保持现有字段，但把逻辑搬到 `tools.historical_impact`，避免后续 BEIDAN/ZUCAI 重复实现。

- [ ] **Step 6: Run gatekeeper**

```bash
python3 standalone_workspace/scripts/qa_deployment_gatekeeper.py
```

Expected: PASS。

---

## Task 2: TicketBuilder 支持 BEIDAN(15) / ZUCAI(14/任九) 以及 ZUCAI play_type

**Files:**
- Modify: `standalone_workspace/tools/ticket_builder.py`
- Test: `standalone_workspace/tests/test_ticket_builder_multi_lottery.py`

- [ ] **Step 1: 写 failing test（BEIDAN 允许 15 legs，ZUCAI 允许 14 legs 且不截断）**

```python
import pytest

from core.recommendation_schema import RecommendationSchema, RecommendedBet
from tools.ticket_builder import LotteryTicketBuilder


def _bet(match_id: str, *, lottery_type: str, play_type: str, selection: str, odds: float | None):
    return RecommendedBet(
        match_id=match_id,
        lottery_type=lottery_type,
        play_type=play_type,
        market="WDL",
        selection=selection,
        prob=0.4,
        odds=odds,
        ev=None,
        edge=None,
        risk_tags=[],
    )


def test_ticket_builder_beidan_allows_15_legs():
    schema = RecommendationSchema(
        recommended_bets=[_bet(f"M{i}", lottery_type="BEIDAN", play_type="BEIDAN_WDL", selection="3", odds=2.5) for i in range(15)]
    )
    res = LotteryTicketBuilder().build_validated_ticket(schema=schema, stake=100.0, date="2026-04-15")
    assert res["ok"] in {True, False}
    assert res["ticket"]
    assert len(res["ticket"]["legs"]) == 15


def test_ticket_builder_zucai_14_match_has_14_legs_and_no_odds():
    schema = RecommendationSchema(
        recommended_bets=[_bet(f"M{i}", lottery_type="ZUCAI", play_type="14_match", selection="3", odds=None) for i in range(14)]
    )
    res = LotteryTicketBuilder().build_validated_ticket(schema=schema, stake=100.0, date="2026-04-15")
    assert res["ticket"]
    assert res["ticket"]["play_type"] == "14_match"
    assert len(res["ticket"]["legs"]) == 14
    assert all("odds" not in leg or leg["odds"] is None for leg in res["ticket"]["legs"])
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest -q standalone_workspace/tests/test_ticket_builder_multi_lottery.py
```

Expected: FAIL（当前会截断至 8 且 play_type 不是 14_match）。

- [ ] **Step 3: 修改 TicketBuilder**

变更点：
1) 根据 `lottery_type` 设定 `max_legs`：JINGCAI=8、BEIDAN=15、ZUCAI=14  
2) ZUCAI 的 `ticket.play_type` 优先取 `b0.play_type`（例如 `renjiu`/`14_match`），不再由 market 推导  
3) ZUCAI legs 不携带 odds（保持 None），让 Router 足彩通道不误判

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest -q standalone_workspace/tests/test_ticket_builder_multi_lottery.py
```

Expected: PASS。

---

## Task 3: Standalone 新增 BeidanWorkflow（北单闭环）

**Files:**
- Create: `standalone_workspace/core/beidan_workflow.py`
- Modify: `standalone_workspace/scripts/mentor_cli.py`
- Test: `standalone_workspace/tests/test_beidan_workflow.py`

- [ ] **Step 1: 写 failing test（北单闭环输出结构 + historical_impact）**

```python
import io
import json

from core.beidan_workflow import BeidanWorkflow
from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore


def test_beidan_workflow_outputs_recommendation_ticket_and_historical_impact(monkeypatch, tmp_path):
    store = SnapshotStore(db_path=str(tmp_path / "snapshots.db"))
    fetcher = MultiSourceFetcher(store=store)

    monkeypatch.setattr(fetcher, "fetch_fixtures_sync", lambda date=None: {"ok": True, "data": {"fixtures": [{"league": "英超", "home_team": "Arsenal", "away_team": "Tottenham", "kickoff_time": "2026-04-15 20:00"}]}, "error": None, "meta": {"mock": True, "source": "test", "confidence": 0.9, "stale": False}})
    monkeypatch.setattr(fetcher, "fetch_odds_sync", lambda home_team, away_team: {"ok": True, "data": {"beidan_sp": {"WDL": {"home": 2.4, "draw": 3.2, "away": 2.9, "handicap": 0}}}, "error": None, "meta": {"mock": True, "source": "test", "confidence": 0.9, "stale": False}})

    wf = BeidanWorkflow(fetcher=fetcher)
    out = wf.run(date="2026-04-15", stake=100.0, auto_trade=False)
    assert out["recommended_bets"]
    assert out["recommended_bets"][0]["lottery_type"] == "BEIDAN"
    assert out["ticket"] is not None
    assert "historical_impact" in out
    assert any(x.get("type") == "historical_impact" for x in (out["audit"].get("explain") or []))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest -q standalone_workspace/tests/test_beidan_workflow.py
```

- [ ] **Step 3: 实现 BeidanWorkflow（最小闭环）**

实现要点：
- fixtures 复用 `MultiSourceFetcher.get_fixtures_normalized`
- odds 使用 `get_odds_normalized(lottery_type="BEIDAN", play_type="BEIDAN_WDL", market="WDL")`
- 调用 OddsAnalyzer（calibrate=True）得到校准与联赛统计
- 推荐 schema：`lottery_type="BEIDAN"`，并在 EV 计算中乘 0.65（返奖率）
- ticket_builder.build_validated_ticket → router/parlay 校验
- settlement 与 pnl 复用 MentorWorkflow 的简化结算方式（90分钟口径）
- 写入 `historical_impact`（顶层）与 `audit.explain`

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest -q standalone_workspace/tests/test_beidan_workflow.py
```

Expected: PASS。

---

## Task 4: Standalone 新增 ZucaiWorkflow（足彩闭环：14/任九）

**Files:**
- Create: `standalone_workspace/core/zucai_workflow.py`
- Modify: `standalone_workspace/scripts/mentor_cli.py`
- Test: `standalone_workspace/tests/test_zucai_workflow.py`

- [ ] **Step 1: 写 failing test（足彩 14_match 闭环可出票校验 + historical_impact 降级正确）**

```python
from core.zucai_workflow import ZucaiWorkflow
from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore


def test_zucai_workflow_builds_14_match_ticket_and_disables_similar_odds(monkeypatch, tmp_path):
    store = SnapshotStore(db_path=str(tmp_path / "snapshots.db"))
    fetcher = MultiSourceFetcher(store=store)

    fixtures = [{"league": "英超", "home_team": f"H{i}", "away_team": f"A{i}", "kickoff_time": "2026-04-15 20:00", "status": "upcoming"} for i in range(14)]
    monkeypatch.setattr(fetcher, "fetch_fixtures_sync", lambda date=None: {"ok": True, "data": {"fixtures": fixtures}, "error": None, "meta": {"mock": True, "source": "test", "confidence": 0.9, "stale": False}})

    wf = ZucaiWorkflow(fetcher=fetcher)
    out = wf.run(date="2026-04-15", stake=100.0, play_type="14_match", auto_trade=False)
    assert out["ticket"] is not None
    assert out["ticket"]["ticket"]["lottery_type"] == "ZUCAI"
    assert out["ticket"]["ticket"]["play_type"] == "14_match"
    assert len(out["ticket"]["ticket"]["legs"]) == 14
    assert out["historical_impact"]["similar_odds"]["enabled"] is False
    assert any("similar_odds_not_applicable" in x for x in out["historical_impact"]["degradations"])
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest -q standalone_workspace/tests/test_zucai_workflow.py
```

- [ ] **Step 3: 实现 ZucaiWorkflow（最小闭环）**

实现要点（符合体彩口径，避免假 EV）：
- 不依赖赔率；每场只做胜平负选材（最小：取主胜作为默认 + 记录降级原因；后续可接入更强模型/统计）
- `RecommendedBet.odds = None`，让 TicketBuilder 不写入 leg odds
- `play_type` 支持 `14_match` 与 `renjiu`
- Router/Parlay 校验：14_match 必须 14 场，renjiu 允许 9-14
- settlement：复用 SettlementEngine 产出的 WDL 结果进行赛后命中判断（闭环的“可结算”先成立）
- `historical_impact`：保留 league_stats（若联赛码可识别），明确降级 `similar_odds_not_applicable:zucai_no_fixed_odds`

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest -q standalone_workspace/tests/test_zucai_workflow.py
```

Expected: PASS。

---

## Task 5: mentor_cli 支持三彩种闭环入口 + 默认离线不联网

**Files:**
- Modify: `standalone_workspace/scripts/mentor_cli.py`
- Modify: `standalone_workspace/tools/multisource_fetcher.py`
- Test: `standalone_workspace/tests/test_mentor_cli.py`

- [ ] **Step 1: 增加 CLI 参数并写 failing test（--lottery-type）**

目标参数：
- `--lottery-type {JINGCAI,BEIDAN,ZUCAI}`（默认 JINGCAI）
- `--zucai-play-type {14_match,renjiu}`（仅 ZUCAI 用，默认 14_match）
- `--online`（默认 off；off 时不得触发 ddgs/web_intel/foreign_api）

- [ ] **Step 2: 实现 offline default**

实现策略（最小变更）：
- 在 `MultiSourceFetcher.__init__` 增加 `online: bool = False`，并在 `get_odds_normalized` 里当 `online=False` 时强制 `skip_browser_fallback=True`、`skip_foreign_api=True`（通过 `_odds_context` 透传已有字段）。
- mentor_cli 默认构造 workflow 时将 fetcher 传入：`MultiSourceFetcher(online=args.online)`，避免 CLI 实盘卡死。

- [ ] **Step 3: 将 mentor_cli 路由到对应 workflow**

规则：
- JINGCAI → MentorWorkflow
- BEIDAN → BeidanWorkflow
- ZUCAI → ZucaiWorkflow

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest -q standalone_workspace/tests/test_mentor_cli.py
```

Expected: PASS。

---

## Task 6: OpenClaw 适配版：mentor_tools 扩展 BEIDAN/ZUCAI 并统一 historical_impact

**Files:**
- Modify: `openclaw_workspace/runtime/football_analyzer/tools/mentor_tools.py`
- Modify: `openclaw_workspace/runtime/football_analyzer/tests/test_mcp_mentor_tools.py`

- [ ] **Step 1: 为 recommend_bets 增加 lottery_type 分支**

规则：
- `lottery_type=jingcai`：保持现有
- `lottery_type=beidan`：EV 乘 0.65，输出 `historical_impact.lottery_type="beidan"`
- `lottery_type=zucai`：odds 可缺省；similar_odds 必须降级；ticket 暂不在工具侧出票（闭环仍由 standalone 负责），但输出必须一致可解释

- [ ] **Step 2: Run tests**

```bash
python3 -m pytest -q openclaw_workspace/runtime/football_analyzer/tests/test_mcp_mentor_tools.py
```

Expected: PASS。

---

## Task 7: Gatekeeper 增强（三彩种闭环 smoke）

**Files:**
- Modify: `standalone_workspace/scripts/qa_deployment_gatekeeper.py`
- Modify/Create: `standalone_workspace/tests/test_closed_loop_trade.py`（扩成三彩种用例）

- [x] **Step 1: 增加 BEIDAN/ZUCAI 的闭环用例**

最小断言：
- 输出包含 `historical_impact`
- `ticket.validation.router.status` 为 VALIDATED/SUCCESS
- 结算字段存在且可产生 pnl（ZUCAI 先按 WDL 口径结算）

- [x] **Step 2: Run gatekeeper**

```bash
python3 standalone_workspace/scripts/qa_deployment_gatekeeper.py
```

Expected: PASS。

---

## Plan Self-Review
- Spec coverage: historical_impact（顶层+explain）已任务化；三彩种闭环分别在 Task 3/4；TicketBuilder 的物理差异在 Task 2；离线默认不联网在 Task 5；OpenClaw 适配一致性在 Task 6；门禁止血在 Task 7。
- Placeholder scan: 无 TBD/TODO；每个任务有明确文件/测试/命令。
- Type consistency: `historical_impact` 字段名与 explain item `type="historical_impact"` 固定；TicketBuilder lottery_type 大写；ZUCAI play_type 使用 `14_match/renjiu`。

---

## Execution Handoff

Plan complete and saved to `standalone_workspace/docs/superpowers/plans/2026-04-16-triple-lottery-ai-native-closed-loop.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
