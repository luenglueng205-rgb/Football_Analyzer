# -*- coding: utf-8 -*-
"""
Dixon-Coles Model — 足球预测工业标准
======================================

相比简单泊松模型，Dixon-Coles 引入两个关键改进：
1. ρ 参数：修正 0-0、1-0、0-1、1-1 的联合概率（低比分偏向）
2. τ 时间衰减：近期比赛权重高，远期比赛指数衰减

数学基础：
- 标准 bivariate Poisson: P(h,a) = Poisson(λ_h) × Poisson(λ_a)
- Dixon-Coles 修正:
    τ₁(x,y) = 1 if x=0 or y=0
    τ₂(x,y) = 1 if x=1 or y=1  
    τ(x,y) = 1 otherwise
    P_DC(h,a) = P(h,a) × [1 - ρ·φ(λ_h)·φ(λ_a)] + ρ·[φ(λ_h,λ_a) if (h,a) in {(0,0),(0,1),(1,0),(1,1)}]

其中 φ 是 Poisson PMF，λ_h = α_i × β_j × γ (主队攻击×客队防守×主场优势)

参考: Dixon & Coles (1997) "Modelling Association Football Scores and Inefficiencies in the Football Betting Market"
"""

from __future__ import annotations

import logging
import math
import numpy as np
from scipy.optimize import minimize
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DixonColesModel:
    """
    Dixon-Coles 双变量泊松模型。
    
    用法：
        model = DixonColesModel()
        model.fit(matches)  # matches: [{"home": "Arsenal", "away": "Chelsea", "hg": 2, "ag": 1, "date": "2025-01-01"}, ...]
        probs = model.predict("Arsenal", "Chelsea")  # {"home_win": 0.52, "draw": 0.26, "away_win": 0.22, "scores": {...}}
    """
    
    # 最多计算到 10-10 的比分矩阵
    MAX_GOALS = 10
    
    def __init__(self, xi: float = 0.001, rho_init: float = -0.13):
        """
        Args:
            xi: 时间衰减参数，越小衰减越快。0.005 = 半衰期约 138 天
            rho_init: ρ 初始值，Dixon-Coles 论文中估计约 -0.13
        """
        self.xi = xi
        self.rho = rho_init
        
        # 团队参数：attack[i], defense[j], home_advantage
        self.attack: Dict[str, float] = {}
        self.defense: Dict[str, float] = {}
        self.home_advantage: float = 0.0
        self.teams: List[str] = []
        
        # 训练元数据
        self._fitted = False
        self._training_matches = 0
        self._best_ll = -np.inf
    
    def _poisson_pmf(self, x: float | np.ndarray, lambda_: float) -> float | np.ndarray:
        """泊松分布 PMF"""
        return (lambda_ ** x) * np.exp(-lambda_) / math.factorial(int(x))
    
    def _tau(self, x: int, y: int) -> float:
        """Dixon-Coles τ 修正函数"""
        if x == 0 and y == 0:
            return 1 - self.rho * (1 / (1 + self.rho))  # 修正 0-0
        elif x == 0 and y == 1:
            return 1 + self.rho / (1 + self.rho)  # 修正 0-1
        elif x == 1 and y == 0:
            return 1 + self.rho / (1 + self.rho)  # 修正 1-0
        elif x == 1 and y == 1:
            return 1 - self.rho  # 修正 1-1
        return 1.0
    
    def _dixon_coles_adj(self, h: int, a: int, lambda_h: float, lambda_a: float) -> float:
        """Dixon-Coles 修正后的联合概率"""
        if h < 0 or a < 0 or h > self.MAX_GOALS or a > self.MAX_GOALS:
            return 0.0
        p_indep = self._poisson_pmf(h, lambda_h) * self._poisson_pmf(a, lambda_a)
        if h <= 1 and a <= 1:
            return p_indep * self._tau(h, a)
        return p_indep
    
    def _log_likelihood(self, params: np.ndarray, matches: List[Dict], 
                        teams: List[str], dates: Optional[List[float]] = None) -> float:
        """
        负对数似然函数（用于 scipy.optimize.minimize）
        
        params 布局: [attack_0, ..., attack_n, defense_0, ..., defense_n, home_adv, rho]
        """
        n = len(teams)
        atk = params[:n]
        dfn = params[n:2*n]
        h_adv = params[2*n]
        rho = params[2*n + 1]
        
        team_to_idx = {t: i for i, t in enumerate(teams)}
        
        ll = 0.0
        def _log_poisson_fn(x, mu):
            return x * math.log(mu) - mu - math.lgamma(x + 1)
        
        for i, m in enumerate(matches):
            hi = team_to_idx.get(m["home"], -1)
            ai = team_to_idx.get(m["away"], -1)
            if hi < 0 or ai < 0:
                continue
            
            w = 1.0
            if dates is not None:
                w = math.exp(-self.xi * dates[i])
            
            exp_h = math.exp(atk[hi] + dfn[ai] + h_adv)
            exp_a = math.exp(atk[ai] + dfn[hi])
            
            hg = int(m.get("hg", m.get("home_goals", 0)))
            ag = int(m.get("ag", m.get("away_goals", 0)))
            
            log_p_h = _log_poisson_fn(hg, exp_h)
            log_p_a = _log_poisson_fn(ag, exp_a)
            
            # Dixon-Coles 修正 (仅对 0-0, 0-1, 1-0, 1-1)
            if hg <= 1 and ag <= 1:
                if hg == 0 and ag == 0:
                    corr = math.log(max(1 - rho * exp_h * exp_a, 1e-10))
                elif hg == 0 and ag == 1:
                    corr = math.log(max(1 + rho * exp_h, 1e-10))
                elif hg == 1 and ag == 0:
                    corr = math.log(max(1 + rho * exp_a, 1e-10))
                elif hg == 1 and ag == 1:
                    corr = math.log(max(1 - rho, 1e-10))
                else:
                    corr = 0.0
                ll += w * (log_p_h + log_p_a + corr)
            else:
                ll += w * (log_p_h + log_p_a)
        
        return -ll
    
    def fit(self, matches: List[Dict], max_iter: int = 500, tol: float = 1e-6) -> Dict:
        """
        拟合 Dixon-Coles 模型。
        
        Args:
            matches: 比赛列表，每个包含 home, away, hg(主队进球), ag(客队进球)
                     可选 date 字段（用于时间衰减）
            max_iter: 最大迭代次数
            tol: 收敛阈值
        
        Returns:
            {"log_likelihood": float, "training_matches": int, "teams": int}
        """
        if not matches:
            raise ValueError("matches 不能为空")
        
        # 提取所有球队
        all_teams = set()
        for m in matches:
            all_teams.add(m["home"])
            all_teams.add(m["away"])
        
        self.teams = sorted(all_teams)
        n = len(self.teams)
        self._training_matches = len(matches)
        
        # 计算时间衰减权重（天差）
        dates = None
        if matches[0].get("date"):
            # 找到最大日期作为参考点
            ref_date = max(m["date"] for m in matches)
            from datetime import datetime
            dates = []
            for m in matches:
                try:
                    d = datetime.strptime(str(m["date"]), "%Y-%m-%d")
                    ref_d = datetime.strptime(str(ref_date), "%Y-%m-%d")
                    dates.append((ref_d - d).days)
                except (ValueError, TypeError):
                    dates.append(0)
        
        # 初始参数
        # attack 初始值：简单主客场平均进球的对数
        home_goals_per_team: Dict[str, List[int]] = {}
        away_goals_per_team: Dict[str, List[int]] = {}
        for m in matches:
            home_goals_per_team.setdefault(m["home"], []).append(int(m.get("hg", 0)))
            away_goals_per_team.setdefault(m["away"], []).append(int(m.get("ag", 0)))
        
        attack_init = np.zeros(n)
        defense_init = np.zeros(n)
        for i, t in enumerate(self.teams):
            hg_list = home_goals_per_team.get(t, [1])
            ag_list = away_goals_per_team.get(t, [1])
            attack_init[i] = np.log(max(np.mean(hg_list), 0.5))
            defense_init[i] = -np.log(max(np.mean(ag_list), 0.5))
        
        home_adv_init = 0.3  # 典型主场优势
        rho_init = -0.13  # Dixon-Coles 论文估计值
        
        params0 = np.concatenate([attack_init, defense_init, [home_adv_init, rho_init]])
        
        # 拟合
        def neg_ll(params):
            return self._log_likelihood(params, matches, self.teams, dates)
        
        result = minimize(
            neg_ll,
            params0,
            method="L-BFGS-B",
            options={"maxiter": max_iter, "ftol": tol}
        )
        
        # 提取参数
        n_teams = len(self.teams)
        for i, t in enumerate(self.teams):
            self.attack[t] = result.x[i]
            self.defense[t] = result.x[n_teams + i]
        self.home_advantage = result.x[2 * n_teams]
        self.rho = result.x[2 * n_teams + 1]
        
        self._best_ll = -result.fun
        self._fitted = True
        
        logger.info(
            f"Dixon-Coles 拟合完成: {n} 球队, {len(matches)} 场比赛, "
            f"log-likelihood={self._best_ll:.1f}, ρ={self.rho:.4f}"
        )
        
        return {
            "log_likelihood": self._best_ll,
            "training_matches": len(matches),
            "teams": n,
            "rho": round(self.rho, 4),
            "home_advantage": round(self.home_advantage, 4)
        }
    
    def predict(self, home: str, away: str, max_goals: int = 8) -> Dict:
        """
        预测某场比赛的胜平负概率和比分矩阵。
        
        Args:
            home: 主队名
            away: 客队名
        
        Returns:
            {
                "home_win": float, "draw": float, "away_win": float,
                "home_goals_expected": float, "away_goals_expected": float,
                "scores": {(h, a): probability, ...},
                "over_2_5": float, "under_2_5": float,
                "btts_yes": float, "btts_no": float
            }
        """
        if not self._fitted:
            raise RuntimeError("模型未拟合，请先调用 fit()")
        
        if home not in self.teams:
            logger.warning(f"主队 {home} 不在训练数据中，使用平均攻击/防守值")
            avg_attack = np.mean(list(self.attack.values()))
            avg_defense = np.mean(list(self.defense.values()))
            attack_h = avg_attack
            defense_h = avg_defense
        else:
            attack_h = self.attack[home]
            defense_h = self.defense[home]
        
        if away not in self.teams:
            logger.warning(f"客队 {away} 不在训练数据中，使用平均攻击/防守值")
            avg_attack = np.mean(list(self.attack.values()))
            avg_defense = np.mean(list(self.defense.values()))
            attack_a = avg_attack
            defense_a = avg_defense
        else:
            attack_a = self.attack[away]
            defense_a = self.defense[away]
        
        # 预期进球
        lambda_h = np.exp(attack_h + defense_a + self.home_advantage)
        lambda_a = np.exp(attack_a + defense_h)
        
        # 构建比分概率矩阵
        scores = {}
        home_win_prob = 0.0
        draw_prob = 0.0
        away_win_prob = 0.0
        over_2_5 = 0.0
        
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                p = self._dixon_coles_adj(h, a, lambda_h, lambda_a)
                scores[(h, a)] = p
                
                if h > a:
                    home_win_prob += p
                elif h == a:
                    draw_prob += p
                else:
                    away_win_prob += p
                
                if h + a > 2.5:
                    over_2_5 += p
        
        # BTTS (双方进球)
        btts_yes = 1.0 - scores.get((0, 0), 0) - sum(
            scores.get((h, 0), 0) for h in range(1, max_goals + 1)
        ) - sum(
            scores.get((0, a), 0) for a in range(1, max_goals + 1)
        )
        
        return {
            "home_win": round(home_win_prob, 4),
            "draw": round(draw_prob, 4),
            "away_win": round(away_win_prob, 4),
            "home_goals_expected": round(lambda_h, 2),
            "away_goals_expected": round(lambda_a, 2),
            "scores": {f"{h}-{a}": round(p, 4) for (h, a), p in sorted(scores.items())},
            "over_2_5": round(over_2_5, 4),
            "under_2_5": round(1 - over_2_5, 4),
            "btts_yes": round(btts_yes, 4),
            "btts_no": round(1 - btts_yes, 4),
        }
    
    def get_team_strength(self, team: str) -> Optional[Dict]:
        """
        获取球队实力参数。
        
        Returns:
            {"attack": float, "defense": float, "overall": float}
            attack > 0 表示进攻强于平均, defense < 0 表示防守好于平均
        """
        if team not in self.teams:
            return None
        
        avg_attack = np.mean(list(self.attack.values()))
        avg_defense = np.mean(list(self.defense.values()))
        
        return {
            "attack": round(self.attack[team] - avg_attack, 3),
            "defense": round(avg_defense - self.defense[team], 3),  # 翻转：正值=防守好
            "overall": round((self.attack[team] - avg_attack) + (avg_defense - self.defense[team]), 3)
        }
    
    def get_league_xg(self, league_matches: List[Dict]) -> Dict[str, float]:
        """
        基于模型参数计算联赛的预期进球基准。
        
        Returns:
            {"avg_home_xg": float, "avg_away_xg": float, "avg_total_xg": float}
        """
        if not self._fitted or not league_matches:
            return {"avg_home_xg": 1.5, "avg_away_xg": 1.1, "avg_total_xg": 2.6}
        
        home_xgs = []
        away_xgs = []
        for m in league_matches:
            home, away = m["home"], m["away"]
            lambda_h = np.exp(self.attack.get(home, 0) + self.defense.get(away, 0) + self.home_advantage)
            lambda_a = np.exp(self.attack.get(away, 0) + self.defense.get(home, 0))
            home_xgs.append(lambda_h)
            away_xgs.append(lambda_a)
        
        return {
            "avg_home_xg": round(np.mean(home_xgs), 2) if home_xgs else 1.5,
            "avg_away_xg": round(np.mean(away_xgs), 2) if away_xgs else 1.1,
            "avg_total_xg": round(np.mean([h + a for h, a in zip(home_xgs, away_xgs)]), 2) if home_xgs else 2.6
        }
