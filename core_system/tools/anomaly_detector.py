from __future__ import annotations


class AnomalyDetector:
    """
    轻量级诱盘/异常检测器（规则引擎）。
    目标：在不引入昂贵推理成本的前提下，快速发现经典庄家陷阱信号。
    """

    def detect_anomaly(
        self,
        home_odds: float,
        draw_odds: float,
        away_odds: float,
        odds_drop_ratio: float = 0.0,
    ) -> dict:
        is_trap = False
        reason = "Normal market behavior."

        if home_odds < 1.30 and odds_drop_ratio > 0.15:
            is_trap = True
            reason = "TRAP: Strong favorite but suspicious sharp money moving against them."
        elif 2.5 <= home_odds <= 2.8 and 2.5 <= away_odds <= 2.8 and draw_odds < 3.2:
            is_trap = True
            reason = "TRAP: Artificially balanced odds to induce draw betting."

        return {"is_trap": is_trap, "reason": reason, "risk_score": 85 if is_trap else 10}

