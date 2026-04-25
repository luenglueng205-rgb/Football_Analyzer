# -*- coding: utf-8 -*-
"""
Backtest Engine — 策略回测框架
================================

用历史数据验证投注策略是否有正期望值（+EV）。

核心指标：
- ROI (Return on Investment): (利润 / 投入) × 100%
- Yield: 每单位投注的平均回报
- Max Drawdown: 最大回撤（从峰值到谷底的最大跌幅）
- Win Rate: 命中率
- CLV (Closing Line Value): 预测概率 vs 终盘赔率隐含概率的差
- Kelly Criterion: 最优投注比例

策略：
1. Pure DC: 只用 Dixon-Coles 预测，当预测概率 > 赔率隐含概率时下注
2. Pure ELO: 只用 ELO 预测
3. Ensemble: DC + ELO 加权融合
4. Kelly: 基于 Kelly 公式计算最优注额
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from tools.dixon_coles import DixonColesModel
from tools.elo_rating import ELORatingSystem
from tools.elo_calibrator import ELOCalibrator

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """单场回测结果"""
    date: str
    league: str
    home: str
    away: str
    home_goals: int
    away_goals: int
    actual_result: str  # H/D/A
    
    # 预测
    dc_probs: Dict[str, float] = field(default_factory=dict)  # Dixon-Coles
    elo_probs: Dict[str, float] = field(default_factory=dict)  # ELO
    ensemble_probs: Dict[str, float] = field(default_factory=dict)  # 融合
    
    # 赔率
    home_odds: float = 0.0
    draw_odds: float = 0.0
    away_odds: float = 0.0
    
    # 投注决策
    bet_side: str = ""  # H/D/A 或 "" (不下注)
    bet_odds: float = 0.0
    kelly_stake: float = 0.0
    
    # 结果
    won: bool = False
    profit: float = 0.0
    
    # CLV
    clv: float = 0.0  # 预测概率 - 赔率隐含概率


@dataclass
class BacktestReport:
    """回测报告"""
    strategy: str
    total_matches: int
    bets_placed: int
    bets_won: int
    win_rate: float
    total_staked: float
    total_profit: float
    roi: float
    max_drawdown: float
    avg_clv: float
    avg_kelly: float
    results: List[BacktestResult] = field(default_factory=list)
    
    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"  回测报告: {self.strategy}",
            f"{'='*60}",
            f"  总场次:     {self.total_matches}",
            f"  下注场次:   {self.bets_placed} ({self.bets_placed/max(self.total_matches,1)*100:.1f}%)",
            f"  命中场次:   {self.bets_won}",
            f"  命中率:     {self.win_rate:.1%}",
            f"  总投注额:   {self.total_staked:.0f} 单位",
            f"  总利润:     {self.total_profit:+.0f} 单位",
            f"  ROI:        {self.roi:+.2%}",
            f"  最大回撤:   {self.max_drawdown:.2%}",
            f"  平均 CLV:   {self.avg_clv:+.4f}",
            f"  平均 Kelly: {self.avg_kelly:.4f}",
            f"{'='*60}",
        ]
        return "\n".join(lines)


class BacktestEngine:
    """
    回测引擎。
    
    用法：
        from tools.dixon_coles import DixonColesModel
        from tools.elo_rating import ELORatingSystem
        
        engine = BacktestEngine(dc_model, elo_system)
        report = engine.run(matches, strategy="ensemble", min_edge=0.03, kelly_fraction=0.25)
        print(report.summary())
    """
    
    def __init__(self, dc_model=None, elo_system=None):
        self.dc = dc_model
        self.elo = elo_system
    
    def _odds_to_implied_probs(self, home_odds: float, draw_odds: float, away_odds: float) -> Tuple[float, float, float]:
        """赔率 → 隐含概率（去除抽水）"""
        total = 1.0 / home_odds + 1.0 / draw_odds + 1.0 / away_odds
        margin = total - 1.0  # 抽水
        return (
            (1.0 / home_odds) / total,
            (1.0 / draw_odds) / total,
            (1.0 / away_odds) / total,
        )
    
    def _ensemble_probs(
        self, dc_probs: Dict[str, float], elo_probs: Dict[str, float], dc_weight: float = 0.6
    ) -> Dict[str, float]:
        """
        Dixon-Coles + ELO 加权融合。
        
        dc_weight: DC 的权重，ELO 的权重为 (1 - dc_weight)
        """
        w_dc = dc_weight
        w_elo = 1.0 - dc_weight
        return {
            "home_win": dc_probs.get("home_win", 0) * w_dc + elo_probs.get("home_win", 0) * w_elo,
            "draw": dc_probs.get("draw", 0) * w_dc + elo_probs.get("draw", 0) * w_elo,
            "away_win": dc_probs.get("away_win", 0) * w_dc + elo_probs.get("away_win", 0) * w_elo,
        }
    
    def _kelly_stake(self, prob: float, odds: float, fraction: float = 0.25) -> float:
        """
        Kelly Criterion（分数 Kelly）。
        
        f* = (b×p - q) / b
        其中 b = odds - 1, p = 预测概率, q = 1 - p
        fraction: Kelly 分数（0.25 = 四分之一 Kelly，控制风险）
        """
        b = odds - 1.0
        p = prob
        q = 1.0 - p
        kelly = (b * p - q) / b
        return max(kelly * fraction, 0.0)  # 负值不下注
    
    def _find_best_bet(
        self,
        probs: Dict[str, float],
        home_odds: float,
        draw_odds: float,
        away_odds: float,
        min_edge: float = 0.03,
        min_odds: float = 1.50,
        max_odds: float = 4.50,
    ) -> Tuple[str, float, float]:
        """
        找到 EV 最高的下注方向（限制赔率范围）。
        
        ⚠️ edge = pred_prob - (1/odds)  【不去抽水！】
        这是判断真实正期望的正确方式：只有预测概率 > 赔率公司的原始隐含概率，才有正EV。
        去掉抽水的隐含概率 < 1/odds，用它比较会产生虚假 CLV 正值（实际是亏钱的）。
        
        Returns:
            (side, odds, edge) 或 ("", 0, 0) 如果没有真实 +EV 的选项
        """
        best_side = ""
        best_edge = 0.0
        best_odds = 0.0
        
        candidates = [
            ("H", probs.get("home_win", 0), home_odds),
            ("D", probs.get("draw", 0), draw_odds),
            ("A", probs.get("away_win", 0), away_odds),
        ]
        
        for side, prob, odds in candidates:
            # 赔率范围过滤
            if odds < min_odds or odds > max_odds:
                continue
            # 真实 edge：预测概率 vs 原始赔率隐含概率（含抽水）
            raw_implied = 1.0 / odds
            edge = prob - raw_implied
            if edge > min_edge and edge > best_edge:
                best_side = side
                best_edge = edge
                best_odds = odds
        
        return best_side, best_odds, best_edge
    
    def run(
        self,
        matches: List[Dict],
        strategy: str = "ensemble",
        min_edge: float = 0.03,
        kelly_fraction: float = 0.25,
        dc_weight: float = 0.6,
        train_window: int = 300,
        step: int = 10,
        min_odds: float = 1.50,
        max_odds: float = 4.50,
    ) -> BacktestReport:
        """
        滚动窗口回测。
        
        用前 train_window 场训练模型，预测后续 match，然后窗口滚动。
        
        Args:
            matches: [{"home", "away", "hg", "ag", "home_odds", "draw_odds", "away_odds", "date", "league"}, ...]
            strategy: "dc" / "elo" / "ensemble" / "calibrated_elo" / "calibrated_ensemble"
            min_edge: 最小 EV edge 才下注
            kelly_fraction: Kelly 分数（0.25 = 四分之一 Kelly）
            dc_weight: DC 在 ensemble 中的权重
            train_window: 训练窗口大小
            step: 每次滚动的步长
            min_odds: 最低赔率限制（过滤低赔无价值下注）
            max_odds: 最高赔率限制（过滤高赔纯赌博）
        
        Returns:
            BacktestReport
        """
        if not matches:
            return BacktestReport(strategy=strategy, total_matches=0, bets_placed=0,
                                  bets_won=0, win_rate=0, total_staked=0, total_profit=0,
                                  roi=0, max_drawdown=0, avg_clv=0, avg_kelly=0)
        
        results: List[BacktestResult] = []
        
        total_matches = len(matches)
        pos = train_window
        
        while pos < total_matches:
            # 训练集
            train = matches[pos - train_window : pos]
            # 测试集（当前窗口）
            test_batch = matches[pos : min(pos + step, total_matches)]
            
            # 训练 Dixon-Coles
            dc_model = None
            if strategy in ("dc", "ensemble", "calibrated_ensemble"):
                try:
                    dc_model = DixonColesModel(xi=0.005)
                    dc_model.fit(train, max_iter=200)
                except Exception as e:
                    logger.warning(f"DC fit failed at pos {pos}: {e}")
            
            # 训练 ELO
            elo_sys = None
            if strategy in ("elo", "ensemble", "calibrated_elo", "calibrated_ensemble"):
                try:
                    elo_sys = ELORatingSystem()
                    elo_sys.update(train)
                except Exception as e:
                    logger.warning(f"ELO fit failed at pos {pos}: {e}")
            
            # 训练 ELO 校准器
            calibrator = None
            if strategy in ("calibrated_elo", "calibrated_ensemble") and elo_sys is not None:
                try:
                    calibrator = ELOCalibrator(home_advantage=elo_sys.home_advantage)
                    calibrator.fit(train, elo_sys)
                except Exception as e:
                    logger.warning(f"ELO Calibrator fit failed at pos {pos}: {e}")
            
            # 预测测试集
            for m in test_batch:
                home = m["home"]
                away = m["away"]
                hg = int(m.get("hg", 0))
                ag = int(m.get("ag", 0))
                actual = "H" if hg > ag else ("A" if hg < ag else "D")
                h_odds = float(m.get("home_odds", 0))
                d_odds = float(m.get("draw_odds", 0))
                a_odds = float(m.get("away_odds", 0))
                
                if h_odds <= 1 or d_odds <= 1 or a_odds <= 1:
                    continue
                
                dc_probs = {}
                elo_probs = {}
                ensemble_probs = {}
                
                try:
                    if dc_model:
                        dc_probs = dc_model.predict(home, away, max_goals=6)
                        dc_probs = {
                            "home_win": dc_probs.get("home_win", 0),
                            "draw": dc_probs.get("draw", 0),
                            "away_win": dc_probs.get("away_win", 0),
                        }
                except Exception:
                    pass
                
                try:
                    if elo_sys:
                        if calibrator and calibrator._fitted:
                            # 校准模式：用 Platt Scaling 替代 Davidson 公式
                            elo_probs = calibrator.predict_from_system(home, away, elo_sys)
                        else:
                            elo_probs = elo_sys.to_probabilities(home, away)
                except Exception:
                    pass
                
                if strategy in ("ensemble", "calibrated_ensemble") and dc_probs and elo_probs:
                    ensemble_probs = self._ensemble_probs(dc_probs, elo_probs, dc_weight)
                elif strategy == "dc" and dc_probs:
                    ensemble_probs = dc_probs
                elif strategy in ("elo", "calibrated_elo") and elo_probs:
                    ensemble_probs = elo_probs
                
                if not ensemble_probs:
                    continue
                
                # 找最佳下注
                bet_side, bet_odds, edge = self._find_best_bet(
                    ensemble_probs, h_odds, d_odds, a_odds, min_edge, min_odds, max_odds
                )
                
                # CLV（正确版本：与原始赔率隐含概率比较，不去抽水）
                if bet_side:
                    side_key = {"H": "home_win", "D": "draw", "A": "away_win"}[bet_side]
                    # 真实 CLV = 预测概率 - 1/odds（不去除抽水，这才是真实超额收益）
                    clv = ensemble_probs.get(side_key, 0) - (1.0 / bet_odds)
                else:
                    clv = 0.0
                
                # Kelly
                if bet_side:
                    kelly = self._kelly_stake(ensemble_probs.get(side_key, 0), bet_odds, kelly_fraction)
                else:
                    kelly = 0.0
                
                # 结算
                won = (bet_side == actual) if bet_side else False
                profit = (bet_odds - 1) * kelly if won else -kelly
                
                result = BacktestResult(
                    date=m.get("date", ""),
                    league=m.get("league", ""),
                    home=home, away=away,
                    home_goals=hg, away_goals=ag,
                    actual_result=actual,
                    dc_probs=dc_probs, elo_probs=elo_probs, ensemble_probs=ensemble_probs,
                    home_odds=h_odds, draw_odds=d_odds, away_odds=a_odds,
                    bet_side=bet_side, bet_odds=bet_odds,
                    kelly_stake=kelly, won=won, profit=profit, clv=clv,
                )
                results.append(result)
            
            pos += step
            if pos % 100 == 0:
                logger.info(f"Backtest progress: {pos}/{total_matches}")
        
        # 计算汇总指标
        bets = [r for r in results if r.bet_side]
        total_staked = sum(r.kelly_stake for r in bets)
        total_profit = sum(r.profit for r in bets)
        bets_won = sum(1 for r in bets if r.won)
        
        # 最大回撤
        peak = 0.0
        max_dd = 0.0
        cum_pnl = 0.0
        for r in bets:
            cum_pnl += r.profit
            peak = max(peak, cum_pnl)
            dd = (peak - cum_pnl) / max(peak, 1e-6)
            max_dd = max(max_dd, dd)
        
        avg_clv = sum(r.clv for r in bets) / max(len(bets), 1)
        avg_kelly = sum(r.kelly_stake for r in bets) / max(len(bets), 1)
        
        return BacktestReport(
            strategy=f"{strategy} (edge>={min_edge}, kelly={kelly_fraction})",
            total_matches=total_matches,
            bets_placed=len(bets),
            bets_won=bets_won,
            win_rate=bets_won / max(len(bets), 1),
            total_staked=total_staked,
            total_profit=total_profit,
            roi=total_profit / max(total_staked, 1e-6),
            max_drawdown=max_dd,
            avg_clv=avg_clv,
            avg_kelly=avg_kelly,
            results=results,
        )


def run_quick_backtest(matches: List[Dict], league: str = "E0", n_matches: int = 2000) -> Dict:
    """
    快速回测入口。
    
    Args:
        matches: 全量历史数据
        league: 联赛代码
        n_matches: 最多使用多少场比赛
    
    Returns:
        {"dc": BacktestReport, "elo": BacktestReport, "ensemble": BacktestReport}
    """
    # 筛选联赛数据 + 标准化字段名
    league_matches = []
    for m in matches:
        if m.get("league") == league:
            league_matches.append({
                "home": m.get("home", m.get("home_team", "")),
                "away": m.get("away", m.get("away_team", "")),
                "hg": m.get("hg", m.get("home_goals", 0)),
                "ag": m.get("ag", m.get("away_goals", 0)),
                "home_odds": m.get("home_odds", 0),
                "draw_odds": m.get("draw_odds", 0),
                "away_odds": m.get("away_odds", 0),
                "date": m.get("date", ""),
                "league": m.get("league", ""),
            })
    league_matches = sorted(league_matches, key=lambda x: x["date"])[:n_matches]
    
    logger.info(f"回测 {league}: {len(league_matches)} 场比赛")
    
    engine = BacktestEngine()
    
    reports = {}
    for strategy in ["dc", "elo", "ensemble", "calibrated_elo", "calibrated_ensemble"]:
        logger.info(f"运行 {strategy} 策略...")
        report = engine.run(
            league_matches,
            strategy=strategy,
            min_edge=0.03,
            kelly_fraction=0.25,
            dc_weight=0.6,
            train_window=min(200, len(league_matches) // 2),
            step=5,
        )
        reports[strategy] = report
        logger.info(f"{strategy}: ROI={report.roi:+.2%}, bets={report.bets_placed}")
    
    return reports
