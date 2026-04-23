import asyncio
import json
from pathlib import Path

from agents.auto_tuner_agent import AutoTunerAgent


def test_evolution_step_updates_hyperparams_and_writes_audit_trail(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AUTO_TUNER_USE_LLM", "0")

    hyperparams_path = tmp_path / "hyperparams.json"
    hyperparams_path.write_text(
        json.dumps(
            {
                "system_version": "1.0.0",
                "last_evolution_date": None,
                "weights": {"fundamental_quant": 0.4, "contrarian_quant": 0.4, "smart_money_quant": 0.2},
                "poisson_engine": {"xg_variance_penalty": 0.05, "draw_bias_adjustment": 1.05},
                "risk_management": {"min_ev_threshold": 1.05, "max_stake_percent": 0.05, "fuzzy_banker_tolerance": 0.8},
                "evolution_memory": {"total_simulations_run": 0, "win_rate": 0.0, "roi": 0.0, "latest_reflection": ""},
                "evolution_audit": {"history": []},
            }
        ),
        encoding="utf-8",
    )

    baseline_report = {
        "total_simulated": 5,
        "wins": 1,
        "win_rate": 0.2,
        "total_profit": -300.0,
        "roi": -0.6,
        "details": [
            {"match": "A vs B", "decision": "3", "actual": "0", "odds": [1.2, 6.0, 10.0], "status": "LOSS", "profit": -100.0},
            {"match": "C vs D", "decision": "3", "actual": "0", "odds": [1.3, 5.0, 9.0], "status": "LOSS", "profit": -100.0},
            {"match": "E vs F", "decision": "1", "actual": "1", "odds": [2.2, 3.2, 3.4], "status": "WIN", "profit": 220.0},
            {"match": "G vs H", "decision": "3", "actual": "0", "odds": [1.25, 5.5, 11.0], "status": "LOSS", "profit": -100.0},
            {"match": "I vs J", "decision": "3", "actual": "0", "odds": [1.4, 4.8, 8.5], "status": "LOSS", "profit": -100.0},
        ],
    }

    agent = AutoTunerAgent(hyperparams_path=str(hyperparams_path), seed=123)
    out = asyncio.run(agent.run_evolution_cycle(baseline_report, seed=123, source_report_path="tmp_backtest_report.json"))
    assert out["ok"] is True

    updated = json.loads(hyperparams_path.read_text(encoding="utf-8"))
    history = updated["evolution_audit"]["history"]
    assert isinstance(history, list) and len(history) == 1
    entry = history[-1]
    assert entry["source_report_path"] == "tmp_backtest_report.json"
    assert entry["baseline"]["total_simulated"] == 5
    assert entry["after"] is None
    assert isinstance(entry["changes"], list) and entry["changes"]

    weights = updated["weights"]
    total_w = float(weights["fundamental_quant"]) + float(weights["contrarian_quant"]) + float(weights["smart_money_quant"])
    assert abs(total_w - 1.0) < 1e-6

    after_report = dict(baseline_report)
    after_report["roi"] = 0.1
    after_report["win_rate"] = 0.6
    after_report["total_profit"] = 50.0
    out2 = agent.attach_comparison(after_report)
    assert out2["ok"] is True

    updated2 = json.loads(hyperparams_path.read_text(encoding="utf-8"))
    entry2 = updated2["evolution_audit"]["history"][-1]
    assert isinstance(entry2.get("after"), dict)
    assert float(entry2["after"]["roi"]) == 0.1
