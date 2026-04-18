from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional, TextIO

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.event_bus import EventBus
from agents.daemon_monitor import RealTimeOddsDaemon, daemon_status, start_daemon, stop_daemon


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="daemon_cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run")
    run_p.add_argument("--match-id", default="match_1024")
    run_p.add_argument("--home-team", default="曼城")
    run_p.add_argument("--away-team", default="切尔西")
    run_p.add_argument("--online", action="store_true")
    run_p.add_argument("--polling-interval-s", type=float, default=2.0)
    run_p.add_argument("--water-drop-threshold", type=float, default=0.08)
    run_p.add_argument("--baseline-home-odds", type=float, default=None)
    run_p.add_argument("--max-ticks", type=int, default=None)
    run_p.add_argument("--pretty", action="store_true")

    start_p = sub.add_parser("start")
    start_p.add_argument("--match-id", default="match_1024")
    start_p.add_argument("--home-team", default="曼城")
    start_p.add_argument("--away-team", default="切尔西")
    start_p.add_argument("--online", action="store_true")
    start_p.add_argument("--polling-interval-s", type=float, default=2.0)
    start_p.add_argument("--water-drop-threshold", type=float, default=0.08)
    start_p.add_argument("--baseline-home-odds", type=float, default=None)

    sub.add_parser("status")

    stop_p = sub.add_parser("stop")
    stop_p.add_argument("--timeout-s", type=float, default=10.0)
    return p


async def _emit(out: TextIO, event: Dict[str, Any], *, pretty: bool) -> None:
    if pretty:
        out.write(json.dumps(event, ensure_ascii=False, indent=2) + "\n")
    else:
        out.write(json.dumps(event, ensure_ascii=False) + "\n")
    out.flush()


def run(argv: Optional[List[str]] = None, *, stdout: Optional[TextIO] = None) -> Dict[str, Any]:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout

    if args.cmd == "status":
        res = daemon_status()
        out.write(json.dumps(res, ensure_ascii=False) + "\n")
        out.flush()
        return res

    if args.cmd == "stop":
        res = stop_daemon(timeout_s=float(args.timeout_s))
        out.write(json.dumps(res, ensure_ascii=False) + "\n")
        out.flush()
        return res

    if args.cmd == "start":
        res = start_daemon(
            match_id=str(args.match_id),
            home_team=str(args.home_team),
            away_team=str(args.away_team),
            online=bool(args.online),
            polling_interval_s=float(args.polling_interval_s),
            water_drop_threshold=float(args.water_drop_threshold),
            baseline_home_odds=args.baseline_home_odds,
        )
        out.write(json.dumps(res, ensure_ascii=False) + "\n")
        out.flush()
        return res

    if args.cmd != "run":
        raise ValueError(f"unknown cmd: {args.cmd}")

    async def _main() -> Dict[str, Any]:
        bus = EventBus()

        async def printer(event: Dict[str, Any]) -> None:
            await _emit(out, event, pretty=bool(args.pretty))

        for t in ("ODDS_DAEMON_STARTED", "ODDS_TICK", "ODDS_ALERT", "ODDS_UNAVAILABLE", "ODDS_DAEMON_STOPPED"):
            bus.subscribe(t, printer)

        daemon = RealTimeOddsDaemon(
            match_id=str(args.match_id),
            home_team=str(args.home_team),
            away_team=str(args.away_team),
            bus=bus,
            online=bool(args.online),
            polling_interval_s=float(args.polling_interval_s),
            water_drop_threshold=float(args.water_drop_threshold),
            baseline_home_odds=args.baseline_home_odds,
        )
        return await daemon.run(max_ticks=args.max_ticks)

    return asyncio.run(_main())


def main(argv: Optional[List[str]] = None) -> int:
    run(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
