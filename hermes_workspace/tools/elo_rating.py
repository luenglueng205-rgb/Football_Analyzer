# -*- coding: utf-8 -*-
"""
ELO Rating System — 球队动态实力评级
======================================

ELO 系统通过"实力再平衡"机制追踪球队动态实力变化：
- 赢了涨分，输了扣分，平局小幅波动
- 大冷门（低 ELO 球队赢高 ELO 球队）→ 加分更多
- 主场优势通过 ELO 加分体现（不直接加到比赛结果上）

与泊松/Dixon-Coles 的区别：
- 泊松：基于进球数的概率模型
- ELO：基于胜负结果的序数模型，捕捉"状态起伏"

两者互补：ELO 衡量"这支队最近强不强"，泊松衡量"这场比赛可能进几个球"。

参考: Elo, A. (1978) "The Rating of Chessplayers, Past and Present"
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ELORatingSystem:
    """
    球队 ELO 等级分系统。
    
    用法：
        elo = ELORatingSystem()
        elo.update(matches)  # [{"home": "Arsenal", "away": "Chelsea", "result": "H", "date": "2025-01-01"}, ...]
        rating = elo.get_rating("Arsenal")  # {"elo": 1650, "form": "+30", "rank": 3}
        odds = elo.to_probabilities("Arsenal", "Chelsea")  # {"home_win": 0.55, ...}
    """
    
    # ELO → 胜率换算常量
    SCALE_FACTOR = 400.0
    
    # 默认参数
    DEFAULT_ELO = 1500.0
    DEFAULT_K = 20.0
    HOME_ADVANTAGE_ELO = 65.0  # 约 58% 主场胜率等价
    
    def __init__(
        self,
        k_factor: float = DEFAULT_K,
        home_advantage: float = HOME_ADVANTAGE_ELO,
        default_elo: float = DEFAULT_ELO,
        k_decay: bool = True,
        draw_nu: float = 0.85,
    ):
        """
        Args:
            k_factor: K 因子，越大 ELO 变化越剧烈
            home_advantage: 主场优势 ELO 值
            default_elo: 新球队的初始 ELO
            k_decay: 是否对低级别联赛使用更小的 K（数据噪声大）
            draw_nu: Davidson 平局参数，越大平局概率越高。英超 ~0.85，意甲 ~1.2
        """
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.default_elo = default_elo
        self.k_decay = k_decay
        self.draw_nu = draw_nu
        
        # 当前 ELO 分
        self.ratings: Dict[str, float] = defaultdict(lambda: self.default_elo)
        
        # 历史记录
        self.history: Dict[str, List[float]] = defaultdict(list)  # team -> [elo_after_match1, ...]
        self.match_count: Dict[str, int] = defaultdict(int)
        
        # 最后更新日期
        self._last_dates: Dict[str, str] = {}
    
    @staticmethod
    def _expected_score(elo_a: float, elo_b: float) -> float:
        """
        计算 A 对 B 的期望得分（0-1）。
        E_A = 1 / (1 + 10^((E_B - E_A) / 400))
        """
        return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / ELORatingSystem.SCALE_FACTOR))
    
    def _get_k(self, team: str, league: str = "") -> float:
        """
        动态 K 因子：
        - 前 30 场：K = 40（快速稳定）
        - 30-100 场：K = 25
        - 100+ 场：K = 20（默认值）
        
        如果启用 k_decay 且联赛数据少，进一步降低 K
        """
        n = self.match_count[team]
        if n < 30:
            k = 40.0
        elif n < 100:
            k = 25.0
        else:
            k = self.k_factor
        
        return k
    
    def update_match(
        self,
        home: str,
        away: str,
        result: str,
        k: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        更新一场比赛后的 ELO。
        
        Args:
            home: 主队
            away: 客队
            result: "H"（主胜）/"D"（平局）/"A"（客胜）
            k: 自定义 K 因子（可选）
        
        Returns:
            {"home_new": float, "away_new": float, "home_change": float, "away_change": float}
        """
        # 实际得分
        if result == "H":
            score_h, score_a = 1.0, 0.0
        elif result == "A":
            score_h, score_a = 0.0, 1.0
        else:  # D
            score_h, score_a = 0.5, 0.5
        
        # 主场调整
        elo_h = self.ratings[home] + self.home_advantage
        elo_a = self.ratings[away]
        
        # 期望得分
        exp_h = self._expected_score(elo_h, elo_a)
        exp_a = 1.0 - exp_h
        
        # K 因子
        k_used = k if k is not None else self._get_k(home)
        
        # ELO 变化
        change_h = k_used * (score_h - exp_h)
        change_a = k_used * (score_a - exp_a)
        
        # 更新评分
        new_h = self.ratings[home] + change_h
        new_a = self.ratings[away] + change_a
        
        self.ratings[home] = new_h
        self.ratings[away] = new_a
        self.match_count[home] += 1
        self.match_count[away] += 1
        self.history[home].append(new_h)
        self.history[away].append(new_a)
        
        return {
            "home_new": round(new_h, 1),
            "away_new": round(new_a, 1),
            "home_change": round(change_h, 1),
            "away_change": round(change_a, 1),
        }
    
    def update(self, matches: List[Dict]) -> Dict:
        """
        批量更新 ELO。
        
        Args:
            matches: [{"home": str, "away": str, "result": "H"/"D"/"A", "date": str}, ...]
        
        Returns:
            {"updated": int, "teams": int}
        """
        # 按日期排序
        sorted_matches = sorted(matches, key=lambda m: m.get("date", ""))
        
        for m in sorted_matches:
            # 从比分推导结果
            result = m.get("result")
            if result not in ("H", "D", "A"):
                hg = m.get("hg", m.get("home_goals", 0))
                ag = m.get("ag", m.get("away_goals", 0))
                if hg > ag:
                    result = "H"
                elif hg < ag:
                    result = "A"
                else:
                    result = "D"
            
            self.update_match(m["home"], m["away"], result)
            self._last_dates[m["home"]] = m.get("date", "")
            self._last_dates[m["away"]] = m.get("date", "")
        
        logger.info(f"ELO 更新完成: {len(sorted_matches)} 场比赛, {len(self.ratings)} 球队")
        return {"updated": len(sorted_matches), "teams": len(self.ratings)}
    
    def get_rating(self, team: str) -> Dict:
        """
        获取球队当前 ELO 评级。
        
        Returns:
            {"elo": float, "matches": int, "form": str, "recent_trend": str}
        """
        elo = self.ratings.get(team, self.default_elo)
        matches = self.match_count.get(team, 0)
        hist = self.history.get(team, [])
        
        # 近期趋势（最近 10 场的 ELO 变化）
        form = ""
        recent_trend = "stable"
        if len(hist) >= 10:
            change_10 = hist[-1] - hist[-10]
            form = f"+{change_10:.0f}" if change_10 >= 0 else f"{change_10:.0f}"
            if change_10 > 30:
                recent_trend = "hot"
            elif change_10 < -30:
                recent_trend = "cold"
            elif change_10 > 10:
                recent_trend = "warming"
            elif change_10 < -10:
                recent_trend = "cooling"
        elif len(hist) >= 5:
            change_5 = hist[-1] - hist[-5]
            form = f"+{change_5:.0f}" if change_5 >= 0 else f"{change_5:.0f}"
        
        return {
            "elo": round(elo, 1),
            "matches": matches,
            "form": form,
            "recent_trend": recent_trend,
        }
    
    def to_probabilities(
        self, home: str, away: str, home_adv_override: Optional[float] = None
    ) -> Dict[str, float]:
        """
        将 ELO 差值转换为胜平负概率。
        
        使用 Davidson（1970）的 draw model：
        - P(H) = 1 / (1 + 10^((Ea-Eh-adv)/400) + ν × 10^((Ea-Eh)/800))
        - P(A) = 1 / (1 + 10^((Eh-Ea+adv)/400) + ν × 10^((Eh-Ea)/800))
        - P(D) = 1 - P(H) - P(A)
        
        ν (nu/draw_nu) 控制平局概率：
        - ν=0.42 → 约 15% 平局率（太低）
        - ν=0.85 → 约 25% 平局率（英超实际 ~26%）
        - ν=1.20 → 约 30% 平局率（意甲实际 ~28%）
        """
        elo_h = self.ratings.get(home, self.default_elo)
        elo_a = self.ratings.get(away, self.default_elo)
        adv = home_adv_override if home_adv_override is not None else self.home_advantage
        
        nu = self.draw_nu
        
        diff_h = elo_a - elo_h - adv
        diff_a = elo_h - elo_a + adv
        
        p_h = 1.0 / (1.0 + 10.0 ** (diff_h / 400.0) + nu * 10.0 ** (diff_h / 800.0))
        p_a = 1.0 / (1.0 + 10.0 ** (diff_a / 400.0) + nu * 10.0 ** (diff_a / 800.0))
        p_d = max(1.0 - p_h - p_a, 0.01)
        
        return {
            "home_win": round(p_h, 4),
            "draw": round(p_d, 4),
            "away_win": round(p_a, 4),
        }
    
    def get_rankings(self, top_n: int = 20) -> List[Dict]:
        """
        获取 ELO 排名。
        
        Returns:
            [{"team": str, "elo": float, "matches": int, "form": str}, ...]
        """
        ranked = []
        for team, elo in self.ratings.items():
            if self.match_count[team] >= 5:  # 至少 5 场才上榜
                info = self.get_rating(team)
                ranked.append({
                    "team": team,
                    "elo": info["elo"],
                    "matches": info["matches"],
                    "form": info["form"],
                    "trend": info["recent_trend"],
                })
        
        ranked.sort(key=lambda x: x["elo"], reverse=True)
        return ranked[:top_n]
    
    def get_elo_after_n_matches(self, team: str, n: int) -> Optional[float]:
        """
        获取球队在第 n 场比赛后的 ELO（用于回测）。
        """
        hist = self.history.get(team, [])
        if n <= len(hist):
            return hist[n - 1]
        return None
    
    def get_form_elo(self, team: str, last_n: int = 10) -> float:
        """
        获取球队近期状态 ELO（最近 N 场的平均 ELO）。
        比"当前 ELO"更能反映"最近状态"。
        """
        hist = self.history.get(team, [])
        if len(hist) < 5:
            return self.ratings.get(team, self.default_elo)
        return round(sum(hist[-last_n:]) / len(hist[-last_n:]), 1)
    
    def detect_form_vs_rating_divergence(self, team: str) -> Dict:
        """
        检测"状态与实力背离"——投注价值信号。
        
        如果球队近期状态 ELO 远高于/低于当前 ELO，说明市场可能低估/高估了该队。
        """
        current = self.ratings.get(team, self.default_elo)
        form = self.get_form_elo(team, last_n=10)
        divergence = form - current
        
        signal = "neutral"
        if divergence > 20:
            signal = "undervalued"  # 状态好但 ELO 还没涨上去 → 可能被低估
        elif divergence < -20:
            signal = "overvalued"  # 状态差但 ELO 还没跌下来 → 可能被高估
        
        return {
            "team": team,
            "current_elo": round(current, 1),
            "form_elo": form,
            "divergence": round(divergence, 1),
            "signal": signal,
        }
