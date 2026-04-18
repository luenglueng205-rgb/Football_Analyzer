import sys
import os
import asyncio
import logging
import argparse
import json
import random
from datetime import datetime, timezone
from json import JSONDecoder
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.backtest_sandbox import BacktestSandbox
from agents.auto_tuner_agent import AutoTunerAgent
from tools.paths import data_dir, datasets_dir

logging.basicConfig(level=logging.INFO, format='%(message)s')

def _now_utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_float(v):
    if isinstance(v, (int, float)):
        return float(v)
    try:
        if v is None:
            return None
        return float(str(v))
    except Exception:
        return None


def _iter_dataset_matches_streaming(filepath: str):
    decoder = JSONDecoder()
    buf = ""
    in_matches = False
    in_array = False
    pos = 0
    with open(filepath, "r", encoding="utf-8") as f:
        while True:
            if pos >= len(buf) - 1024:
                chunk = f.read(1024 * 256)
                if not chunk:
                    break
                buf = buf[pos:] + chunk
                pos = 0

            if not in_matches:
                idx = buf.find('"matches"', pos)
                if idx < 0:
                    pos = max(0, len(buf) - 16)
                    continue
                pos = idx + len('"matches"')
                in_matches = True

            if in_matches and not in_array:
                lb = buf.find("[", pos)
                if lb < 0:
                    pos = max(0, len(buf) - 16)
                    continue
                pos = lb + 1
                in_array = True

            if not in_array:
                continue

            while True:
                while pos < len(buf) and buf[pos] in " \r\n\t,":
                    pos += 1
                if pos >= len(buf):
                    break
                if buf[pos] == "]":
                    return
                try:
                    obj, end = decoder.raw_decode(buf, pos)
                except json.JSONDecodeError:
                    break
                pos = end
                if isinstance(obj, dict):
                    yield obj


def _normalize_raw_match(raw: dict):
    home = raw.get("home_team") or raw.get("主队") or raw.get("home") or raw.get("主队名称")
    away = raw.get("away_team") or raw.get("客队") or raw.get("away") or raw.get("客队名称")

    home_odds = _safe_float(raw.get("home_odds") or raw.get("主队赔率") or raw.get("odds_home") or raw.get("home"))
    draw_odds = _safe_float(raw.get("draw_odds") or raw.get("平局赔率") or raw.get("odds_draw") or raw.get("draw"))
    away_odds = _safe_float(raw.get("away_odds") or raw.get("客队赔率") or raw.get("odds_away") or raw.get("away"))

    hg = raw.get("home_goals") if raw.get("home_goals") is not None else raw.get("主队进球")
    ag = raw.get("away_goals") if raw.get("away_goals") is not None else raw.get("客队进球")
    if hg is None and raw.get("home_score") is not None:
        hg = raw.get("home_score")
    if ag is None and raw.get("away_score") is not None:
        ag = raw.get("away_score")
    try:
        hg_i = int(hg)
        ag_i = int(ag)
    except Exception:
        hg_i = None
        ag_i = None

    if not home or not away:
        return None
    if home_odds is None or draw_odds is None or away_odds is None:
        return None
    if hg_i is None or ag_i is None:
        return None

    if hg_i > ag_i:
        actual = "3"
    elif hg_i == ag_i:
        actual = "1"
    else:
        actual = "0"

    return {"home": str(home), "away": str(away), "pre_match_odds": [home_odds, draw_odds, away_odds], "actual_result": actual}


def _load_real_historical_matches(*, dataset_path: str, sample_size: int, seed: int, max_scan: int):
    rng = random.Random(int(seed))
    reservoir = []
    seen = 0
    for raw in _iter_dataset_matches_streaming(dataset_path):
        if seen >= int(max_scan):
            break
        seen += 1
        norm = _normalize_raw_match(raw)
        if not norm:
            continue
        if len(reservoir) < sample_size:
            reservoir.append(norm)
            continue
        j = rng.randint(0, seen - 1)
        if j < sample_size:
            reservoir[j] = norm
    return reservoir


def _persist_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _load_report(path: Path):
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError("report json must be object")
    matches = obj.get("matches")
    baseline = obj.get("baseline_report") or obj.get("pnl_report")
    if not isinstance(matches, list) or not isinstance(baseline, dict):
        raise ValueError("report missing matches/baseline_report")
    return matches, baseline

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=str, default="", help="已有回测报告 JSON（包含 matches/baseline_report）")
    parser.add_argument("--dataset", type=str, default="", help="历史数据集 JSON（默认使用 openclaw datasets/raw）")
    parser.add_argument("--sample-size", type=int, default=80)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-scan", type=int, default=30000)
    args = parser.parse_args()

    print("\n🚀 [系统点火] 启动时光机与进化引擎...")

    report_path = Path(args.report).expanduser().resolve() if args.report else None
    source_report_path = str(report_path) if report_path else None
    if report_path:
        matches, baseline_report = _load_report(report_path)
    else:
        dataset_path = args.dataset or datasets_dir("raw", "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json")
        dataset_path = str(Path(dataset_path).expanduser().resolve())
        matches = _load_real_historical_matches(
            dataset_path=dataset_path, sample_size=int(args.sample_size), seed=int(args.seed), max_scan=int(args.max_scan)
        )
        if not matches:
            raise SystemExit(f"未能从数据集提取可回测样本: {dataset_path}")
        sandbox = BacktestSandbox()
        baseline_report = sandbox.run_batch_simulation(matches)
        out_dir = Path(data_dir("backtest_reports"))
        report_path = out_dir / f"backtest_report_{_now_utc_compact()}.json"
        payload = {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dataset_path": dataset_path,
            "sample_size": int(args.sample_size),
            "seed": int(args.seed),
            "max_scan": int(args.max_scan),
            "matches": matches,
            "baseline_report": baseline_report,
        }
        _persist_json(report_path, payload)
        source_report_path = str(report_path)

    tuner = AutoTunerAgent(seed=int(args.seed))
    await tuner.run_evolution_cycle(baseline_report, seed=int(args.seed), source_report_path=source_report_path)

    sandbox2 = BacktestSandbox()
    after_report = sandbox2.run_batch_simulation(matches)
    tuner.attach_comparison(after_report)

    compare_path = Path(data_dir("backtest_reports")) / f"evolution_compare_{_now_utc_compact()}.json"
    _persist_json(
        compare_path,
        {"schema_version": "1.0", "source_report_path": source_report_path, "baseline_report": baseline_report, "after_report": after_report},
    )

    print("📌 对比报告已保存:", str(compare_path))
    
if __name__ == "__main__":
    asyncio.run(main())
