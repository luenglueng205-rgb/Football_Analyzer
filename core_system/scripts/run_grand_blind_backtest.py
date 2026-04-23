import argparse
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.backtest_sandbox import BacktestSandbox

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main():
    parser = argparse.ArgumentParser(description="Grand blind backtest on COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json")
    parser.add_argument("--dataset-path", default=None)
    parser.add_argument("--lottery-type", default="JINGCAI", choices=["JINGCAI", "BEIDAN", "ZUCAI"])
    parser.add_argument("--play-type", default="", help="JINGCAI/BEIDAN: WDL|MIXED_PARLAY|...  ZUCAI: 14_match|renjiu|6_htft|4_goals")
    parser.add_argument("--stake", type=float, default=100.0)
    parser.add_argument("--max-matches", type=int, default=None)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--dataset-mode", default="stream", choices=["stream", "load_all"])
    parser.add_argument("--sample-strategy", default="first", choices=["first", "reservoir"])
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    sandbox = BacktestSandbox()
    report = sandbox.run_grand_blind_backtest(
        dataset_path=args.dataset_path,
        lottery_type=args.lottery_type,
        play_type=args.play_type,
        stake=args.stake,
        max_matches=args.max_matches,
        seed=args.seed,
        dataset_mode=args.dataset_mode,
        sample_strategy=args.sample_strategy,
        output_dir=args.output_dir,
    )
    print("\n" + "=" * 70)
    print("✅ Grand Blind Backtest 完成")
    print("=" * 70)
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    print(f"run_id: {report.get('run_id')}")
    print(f"tickets_validated: {summary.get('tickets_validated')}  rejected: {summary.get('tickets_rejected')}")
    print(f"pnl_total: {summary.get('pnl_total')}  roi: {summary.get('roi')}  win_rate: {summary.get('win_rate')}")
    print(f"report_json: {report.get('report_path')}")
    print(f"report_md:   {report.get('report_md_path')}")


if __name__ == "__main__":
    main()
