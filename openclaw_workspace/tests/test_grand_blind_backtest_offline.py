import json
from pathlib import Path

from tools.backtest_sandbox import BacktestSandbox


def test_grand_blind_backtest_jingcai_wdl_offline_fixture(tmp_path):
    fixture = Path(__file__).parent / "fixtures" / "complete_football_data_mini.json"
    sandbox = BacktestSandbox()
    report = sandbox.run_grand_blind_backtest(
        dataset_path=str(fixture),
        lottery_type="JINGCAI",
        play_type="WDL",
        stake=100.0,
        max_matches=14,
        seed=7,
        dataset_mode="stream",
        sample_strategy="first",
        output_dir=str(tmp_path),
        keep_examples=5,
    )

    summary = report.get("summary")
    assert summary["tickets_total"] == 14
    assert summary["tickets_validated"] == 14
    assert summary["tickets_rejected"] == 0
    assert summary["stake_total"] == 1400.0
    assert summary["pnl_total"] == -195.0

    report_path = Path(report["report_path"])
    md_path = Path(report["report_md_path"])
    assert report_path.exists()
    assert md_path.exists()

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["lottery_type"] == "JINGCAI"
    assert payload["play_type"] == "WDL"
    assert payload["historical_impact_aggregates"]["matches_total"] == 14


def test_grand_blind_backtest_zucai_14_match_offline_fixture(tmp_path):
    fixture = Path(__file__).parent / "fixtures" / "complete_football_data_mini.json"
    sandbox = BacktestSandbox()
    report = sandbox.run_grand_blind_backtest(
        dataset_path=str(fixture),
        lottery_type="ZUCAI",
        play_type="14_match",
        stake=100.0,
        max_matches=14,
        seed=7,
        dataset_mode="stream",
        sample_strategy="first",
        output_dir=str(tmp_path),
        keep_examples=2,
    )

    summary = report.get("summary")
    assert summary["tickets_total"] == 1
    assert summary["tickets_validated"] == 1
    assert summary["tickets_rejected"] == 0
    assert summary["stake_total"] == 100.0
    assert summary["pnl_total"] == -100.0
