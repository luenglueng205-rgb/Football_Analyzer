from dataclasses import dataclass
import math
from typing import Dict, Optional


@dataclass(frozen=True)
class MarketProbabilityEngine:
    max_goals: int = 7
    max_score: int = 6

    def implied_probabilities_from_odds(self, odds: Dict[str, Optional[float]]) -> Dict[str, float]:
        inv: Dict[str, float] = {}
        for k, v in (odds or {}).items():
            try:
                fv = float(v)
            except Exception:
                continue
            if fv <= 0:
                continue
            inv[str(k)] = 1.0 / fv

        s = sum(inv.values())
        if s <= 0:
            return {str(k): 0.0 for k in (odds or {}).keys()}
        return {k: v / s for k, v in inv.items()}

    def _poisson_pmf(self, k: int, mu: float) -> float:
        if k < 0:
            return 0.0
        if mu <= 0:
            return 1.0 if k == 0 else 0.0
        return math.exp(-mu) * (mu**k) / math.factorial(k)

    def wdl_from_xg(self, home_xg: float, away_xg: float) -> Dict[str, float]:
        p_home = 0.0
        p_draw = 0.0
        p_away = 0.0

        for h in range(0, self.max_score + 1):
            ph = self._poisson_pmf(h, home_xg)
            for a in range(0, self.max_score + 1):
                pa = self._poisson_pmf(a, away_xg)
                p = ph * pa
                if h > a:
                    p_home += p
                elif h == a:
                    p_draw += p
                else:
                    p_away += p

        s = p_home + p_draw + p_away
        if s <= 0:
            return {"3": 0.0, "1": 0.0, "0": 0.0}
        return {"3": p_home / s, "1": p_draw / s, "0": p_away / s}

    def handicap_wdl_from_xg(self, home_xg: float, away_xg: float, handicap: float) -> Dict[str, float]:
        p_home = 0.0
        p_draw = 0.0
        p_away = 0.0

        for h in range(0, self.max_score + 1):
            ph = self._poisson_pmf(h, home_xg)
            for a in range(0, self.max_score + 1):
                pa = self._poisson_pmf(a, away_xg)
                p = ph * pa
                diff = (h + handicap) - a
                if diff > 0:
                    p_home += p
                elif diff == 0:
                    p_draw += p
                else:
                    p_away += p

        s = p_home + p_draw + p_away
        if s <= 0:
            return {"3": 0.0, "1": 0.0, "0": 0.0}
        return {"3": p_home / s, "1": p_draw / s, "0": p_away / s}

    def goals_distribution(self, home_xg: float, away_xg: float) -> Dict[str, float]:
        mu = max(0.0, home_xg + away_xg)
        dist: Dict[str, float] = {}

        p_tail = 0.0
        for g in range(0, self.max_goals + 1):
            dist[str(g)] = self._poisson_pmf(g, mu)

        for g in range(self.max_goals + 1, self.max_goals + 10):
            p_tail += self._poisson_pmf(g, mu)

        dist["7+"] = dist.pop(str(self.max_goals)) + p_tail

        s = sum(dist.values())
        if s <= 0:
            return {k: 0.0 for k in dist}
        return {k: v / s for k, v in dist.items()}

    def cs_topk(self, home_xg: float, away_xg: float, k: int = 10) -> Dict[str, float]:
        pairs = []
        for h in range(0, self.max_score + 1):
            ph = self._poisson_pmf(h, home_xg)
            for a in range(0, self.max_score + 1):
                pa = self._poisson_pmf(a, away_xg)
                pairs.append((f"{h}-{a}", ph * pa))

        pairs.sort(key=lambda x: x[1], reverse=True)
        top = dict(pairs[: max(1, int(k))])
        s = sum(top.values())
        if s <= 0:
            return {k: 0.0 for k in top}
        return {k: v / s for k, v in top.items()}
