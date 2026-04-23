from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, TextIO

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.mentor_workflow import MentorWorkflow
from tools.multisource_fetcher import MultiSourceFetcher


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mentor_cli")
    p.add_argument("--date", default="2026-04-15")
    p.add_argument("--lottery-type", default="JINGCAI", choices=["JINGCAI", "BEIDAN", "ZUCAI"])
    p.add_argument("--zucai-play-type", default="14_match", choices=["14_match", "renjiu"])
    p.add_argument("--online", action="store_true")
    p.add_argument("--match-id", default=None)
    p.add_argument("--match-index", type=int, default=0)
    p.add_argument("--stake", type=float, default=100.0)
    p.add_argument("--auto-trade", action="store_true")
    p.add_argument("--current-score", default="1-0")
    p.add_argument("--current-minute", type=int, default=76)
    p.add_argument("--live-odds-against", type=float, default=4.5)
    p.add_argument("--ft-score-fallback", default="2-1")
    p.add_argument("--pretty", action="store_true")
    return p


def _construct_workflow(workflow_cls, *, fetcher: MultiSourceFetcher):
    import inspect

    try:
        sig = inspect.signature(workflow_cls)
    except Exception:
        sig = None

    if sig is not None and "fetcher" in sig.parameters:
        return workflow_cls(fetcher=fetcher)
    wf = workflow_cls()
    if hasattr(wf, "fetcher"):
        setattr(wf, "fetcher", fetcher)
    return wf


def run(
    argv: Optional[List[str]] = None,
    *,
    workflow: Optional[Any] = None,
    stdout: Optional[TextIO] = None,
) -> Dict[str, Any]:
    args = build_parser().parse_args(argv)
    lt = str(args.lottery_type or "JINGCAI").upper()
    wf = workflow
    if wf is None:
        fetcher = MultiSourceFetcher(online=bool(args.online))
        if lt == "BEIDAN":
            from core.beidan_workflow import BeidanWorkflow

            wf = _construct_workflow(BeidanWorkflow, fetcher=fetcher)
        elif lt == "ZUCAI":
            from core.zucai_workflow import ZucaiWorkflow

            wf = _construct_workflow(ZucaiWorkflow, fetcher=fetcher)
        else:
            wf = MentorWorkflow(fetcher=fetcher)

    import inspect

    run_fn = getattr(wf, "run")
    sig = inspect.signature(run_fn)
    kwargs: Dict[str, Any] = {
        "date": args.date,
        "match_id": args.match_id,
        "match_index": args.match_index,
        "stake": args.stake,
        "auto_trade": bool(args.auto_trade),
        "current_score": args.current_score,
        "current_minute": args.current_minute,
        "live_odds_against": args.live_odds_against,
        "ft_score_fallback": args.ft_score_fallback,
        "play_type": args.zucai_play_type,
    }
    result = run_fn(**{k: v for k, v in kwargs.items() if k in sig.parameters})

    out = stdout or sys.stdout
    if args.pretty:
        out.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        out.write(json.dumps(result, ensure_ascii=False) + "\n")
    return result


def main(argv: Optional[List[str]] = None) -> int:
    run(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
