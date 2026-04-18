# -*- coding: utf-8 -*-

import json
import os
from collections import defaultdict
from typing import Any, Dict

from tools.paths import data_dir, datasets_dir


class HistoricalDatabase:
    def __init__(self, lazy_load: bool = True):
        self.lazy_load = lazy_load
        self._raw_data: Dict[str, Any] | None = None
        self._league_stats: Dict[str, Dict[str, Any]] | None = None
        self.league_mapping: Dict[str, Any] = {}
        self._load_league_mapping()

    def _load_league_mapping(self) -> None:
        mapping_file = os.path.join(data_dir(), "league_mapping.json")
        if os.path.exists(mapping_file):
            with open(mapping_file, "r", encoding="utf-8") as f:
                self.league_mapping = json.load(f)

    @property
    def raw_data(self) -> Dict[str, Any]:
        if self._raw_data is None:
            filepath = os.path.join(datasets_dir(), "raw", "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json")
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    self._raw_data = json.load(f)
            else:
                self._raw_data = {"metadata": {}, "matches": []}
        return self._raw_data

    def get_league_stats(self, league_code: str) -> Dict[str, Any]:
        if self._league_stats is None:
            self._calculate_all_league_stats()
        return self._league_stats.get(league_code, {
            "avg_total_goals": 2.7,
            "home_win_rate": 0.45,
            "draw_rate": 0.25,
            "away_win_rate": 0.30,
            "over_2_5_rate": 0.52,
            "btts_yes_rate": 0.47,
            "sample_size": 0,
        })

    def _calculate_all_league_stats(self) -> None:
        self._league_stats = {}
        matches = (self.raw_data or {}).get("matches", [])
        if not matches:
            return

        league_matches: Dict[str, list] = defaultdict(list)
        for m in matches:
            league = m.get("league", "unknown")
            league_matches[league].append(m)

        import statistics

        for league, league_data in league_matches.items():
            if len(league_data) < 100:
                continue
            home_goals = [m.get("home_goals", 0) for m in league_data if m.get("home_goals") is not None]
            away_goals = [m.get("away_goals", 0) for m in league_data if m.get("away_goals") is not None]
            results = [m.get("result", "H") for m in league_data]
            if not home_goals:
                continue
            total_goals = [h + a for h, a in zip(home_goals, away_goals)]
            self._league_stats[league] = {
                "avg_total_goals": statistics.mean(total_goals) if total_goals else 2.6,
                "home_win_rate": results.count("H") / len(results) if results else 0.44,
                "draw_rate": results.count("D") / len(results) if results else 0.26,
                "away_win_rate": results.count("A") / len(results) if results else 0.30,
                "over_2_5_rate": sum(1 for t in total_goals if t > 2.5) / len(total_goals) if total_goals else 0.52,
                "btts_yes_rate": sum(1 for m in league_data if m.get("home_goals", 0) > 0 and m.get("away_goals", 0) > 0) / len(league_data) if league_data else 0.47,
                "sample_size": len(league_data),
            }


_history_db: HistoricalDatabase | None = None


def get_historical_database(lazy_load: bool = True) -> HistoricalDatabase:
    global _history_db
    if _history_db is None:
        _history_db = HistoricalDatabase(lazy_load=lazy_load)
    return _history_db

