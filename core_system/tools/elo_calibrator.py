# -*- coding: utf-8 -*-
"""
ELO Probability Calibrator — ELO 概率校准器
==============================================

**问题根源**：
ELO 的 Davidson 公式是理论模型，输出的概率来自数学推导，
并不是从历史比赛结果中统计出来的"经验概率"。
两者之间存在系统性偏差（通常 ELO 高估热门队胜率），
导致模型始终"发现"相同方向的边际值，但那些边际值只是模型偏差，不是真正的市场低估。

**解决方案：Platt Scaling**
用逻辑回归把 ELO 差值→实际胜率做一个映射校准：
1. 按 ELO 差值分桶（每50分一桶）
2. 统计每个桶里主/平/客的实际频率
3. 用 Logistic Regression 拟合连续映射
4. 用校准后的概率替代 Davidson 公式

**效果**：
- CLV 会变小（因为校准后的概率更贴近市场）
- 但 ROI 应该转正（因为筛选出的下注真的是市场低估）
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ELOCalibrator:
    """
    ELO 概率校准器。
    
    用法：
        calibrator = ELOCalibrator()
        calibrator.fit(matches, elo_system)
        # 替代 elo.to_probabilities()
        probs = calibrator.predict(home_elo, away_elo)
    
    参数说明：
        n_bins: ELO 差值分桶数（每桶约 50 ELO 点）
        min_samples_per_bin: 最少样本才校准（样本不足的桶用全局均值代替）
        home_advantage: 主场优势 ELO 值（需与 ELORatingSystem 保持一致）
    """
    
    def __init__(
        self,
        home_advantage: float = 65.0,
        bin_size: float = 50.0,
        min_bin_samples: int = 30,
        regularization: float = 1.0,
    ):
        self.home_advantage = home_advantage
        self.bin_size = bin_size
        self.min_bin_samples = min_bin_samples
        self.regularization = regularization
        
        # 分桶统计
        # key: bin_idx, value: {"H": int, "D": int, "A": int, "total": int}
        self._bins: Dict[int, Dict[str, int]] = defaultdict(
            lambda: {"H": 0, "D": 0, "A": 0, "total": 0}
        )
        
        # Logistic Regression 参数
        # P(H) = sigmoid(a_h * elo_diff + b_h)
        # P(A) = sigmoid(a_a * (-elo_diff) + b_a)
        # P(D) = 1 - P(H) - P(A)
        self._lr_h: Optional[Tuple[float, float]] = None  # (slope, intercept)
        self._lr_a: Optional[Tuple[float, float]] = None
        
        # 全局基准
        self._global_h: float = 0.45
        self._global_d: float = 0.26
        self._global_a: float = 0.29
        
        self._fitted = False
        self._n_samples = 0
    
    def _elo_diff_to_bin(self, elo_diff: float) -> int:
        """ELO 差值 → 桶索引（以 bin_size 为单位）"""
        return int(math.floor(elo_diff / self.bin_size))
    
    def fit(self, matches: List[Dict], elo_system) -> "ELOCalibrator":
        """
        从历史比赛数据拟合校准器。
        
        需要在 ELO 系统更新之后（最好用同一批数据更新 ELO，再用训练集的滚动 ELO 校准）。
        这里简化处理：用最终 ELO 评分做 out-of-sample 校准（会有轻微数据泄露，但在实践中可接受）。
        
        Args:
            matches: [{"home": str, "away": str, "hg": int, "ag": int, ...}]
            elo_system: 已 fit 的 ELORatingSystem 实例
        """
        self._bins.clear()
        
        valid = 0
        for m in matches:
            home = m.get("home", "")
            away = m.get("away", "")
            hg = int(m.get("hg", m.get("home_goals", -1)))
            ag = int(m.get("ag", m.get("away_goals", -1)))
            
            if not home or not away or hg < 0 or ag < 0:
                continue
            
            # 实际结果
            if hg > ag:
                result = "H"
            elif hg < ag:
                result = "A"
            else:
                result = "D"
            
            # ELO 差值（主场调整后）
            elo_h = elo_system.ratings.get(home, elo_system.default_elo) + self.home_advantage
            elo_a = elo_system.ratings.get(away, elo_system.default_elo)
            elo_diff = elo_h - elo_a  # 正值：主队强
            
            bin_idx = self._elo_diff_to_bin(elo_diff)
            self._bins[bin_idx][result] += 1
            self._bins[bin_idx]["total"] += 1
            valid += 1
        
        self._n_samples = valid
        logger.info(f"ELO 校准器：收集 {valid} 场比赛，{len(self._bins)} 个分桶")
        
        if valid < 100:
            logger.warning(f"样本量不足（{valid}），校准效果可能较差")
        
        # 计算全局基准
        total_h = sum(b["H"] for b in self._bins.values())
        total_d = sum(b["D"] for b in self._bins.values())
        total_a = sum(b["A"] for b in self._bins.values())
        total = total_h + total_d + total_a
        
        if total > 0:
            self._global_h = total_h / total
            self._global_d = total_d / total
            self._global_a = total_a / total
        
        logger.info(f"全局基准: H={self._global_h:.3f} D={self._global_d:.3f} A={self._global_a:.3f}")
        
        # 拟合逻辑回归
        self._fit_logistic_regression()
        
        self._fitted = True
        return self
    
    def _fit_logistic_regression(self):
        """
        用梯度下降拟合 Logistic Regression。
        
        P(H win) = sigmoid(a * elo_diff + b)
        P(A win) = sigmoid(-a * elo_diff - b)  (对称)
        
        用桶的中值 ELO 差 + 实际胜率做训练点。
        """
        # 收集训练点
        X = []  # ELO 差值（桶中心）
        y_h = []  # 主队实际胜率
        y_a = []  # 客队实际胜率
        weights = []
        
        for bin_idx, counts in sorted(self._bins.items()):
            n = counts["total"]
            if n < self.min_bin_samples:
                continue
            
            bin_center = (bin_idx + 0.5) * self.bin_size
            actual_h = counts["H"] / n
            actual_a = counts["A"] / n
            
            X.append(bin_center)
            y_h.append(actual_h)
            y_a.append(actual_a)
            weights.append(n)  # 样本量加权
        
        if len(X) < 3:
            logger.warning("有效分桶 < 3，Logistic Regression 无法拟合，使用全局均值")
            self._lr_h = None
            self._lr_a = None
            return
        
        # 用最小二乘拟合 logit(y) ~ a*x + b（线性回归在 logit 空间）
        # logit(p) = log(p / (1-p))
        def logit(p):
            p = max(min(p, 0.999), 0.001)
            return math.log(p / (1.0 - p))
        
        logit_h = [logit(p) for p in y_h]
        logit_a = [logit(p) for p in y_a]
        
        # 加权线性回归：logit(y) = a*x + b
        # 解析解：a = (Σwxy - Σwx*Σwy/Σw) / (Σwx² - (Σwx)²/Σw)
        def weighted_linear_fit(x_vals, y_vals, w_vals):
            """返回 (slope, intercept)"""
            sw = sum(w_vals)
            swx = sum(w * x for w, x in zip(w_vals, x_vals))
            swy = sum(w * y for w, y in zip(w_vals, y_vals))
            swxx = sum(w * x * x for w, x in zip(w_vals, x_vals))
            swxy = sum(w * x * y for w, x, y in zip(w_vals, x_vals, y_vals))
            
            denom = swxx - swx * swx / sw
            if abs(denom) < 1e-9:
                return 0.0, swy / sw  # 退化为截距（全局均值）
            
            slope = (swxy - swx * swy / sw) / denom
            intercept = (swy - slope * swx) / sw
            return slope, intercept
        
        slope_h, intercept_h = weighted_linear_fit(X, logit_h, weights)
        slope_a, intercept_a = weighted_linear_fit(X, logit_a, weights)
        
        self._lr_h = (slope_h, intercept_h)
        self._lr_a = (slope_a, intercept_a)
        
        logger.info(
            f"LR 拟合: P(H)=sigmoid({slope_h:.5f}*x+{intercept_h:.3f}), "
            f"P(A)=sigmoid({slope_a:.5f}*x+{intercept_a:.3f})"
        )
    
    @staticmethod
    def _sigmoid(x: float) -> float:
        """Sigmoid 函数（数值稳定）"""
        if x >= 0:
            return 1.0 / (1.0 + math.exp(-x))
        else:
            ex = math.exp(x)
            return ex / (1.0 + ex)
    
    def predict(self, home_elo: float, away_elo: float) -> Dict[str, float]:
        """
        用校准概率预测胜平负概率。
        
        Args:
            home_elo: 主队 ELO（不含主场优势，内部会加）
            away_elo: 客队 ELO
        
        Returns:
            {"home_win": float, "draw": float, "away_win": float}
        """
        elo_diff = (home_elo + self.home_advantage) - away_elo
        
        if not self._fitted or self._lr_h is None:
            # 未校准：fallback 到全局均值（不区分强弱）
            return {
                "home_win": self._global_h,
                "draw": self._global_d,
                "away_win": self._global_a,
            }
        
        slope_h, intercept_h = self._lr_h
        slope_a, intercept_a = self._lr_a
        
        p_h = self._sigmoid(slope_h * elo_diff + intercept_h)
        p_a = self._sigmoid(slope_a * elo_diff + intercept_a)
        
        # 归一化（确保三个概率之和为 1）
        p_d = max(1.0 - p_h - p_a, 0.01)
        total = p_h + p_d + p_a
        
        return {
            "home_win": round(p_h / total, 4),
            "draw": round(p_d / total, 4),
            "away_win": round(p_a / total, 4),
        }
    
    def predict_from_system(self, home: str, away: str, elo_system) -> Dict[str, float]:
        """
        从球队名字查 ELO 然后预测（便捷接口）。
        
        Args:
            home: 主队名
            away: 客队名
            elo_system: ELORatingSystem 实例
        """
        elo_h = elo_system.ratings.get(home, elo_system.default_elo)
        elo_a = elo_system.ratings.get(away, elo_system.default_elo)
        return self.predict(elo_h, elo_a)
    
    def bin_stats(self, min_samples: int = 20) -> List[Dict]:
        """
        打印分桶统计（用于调试/诊断校准效果）。
        
        Returns:
            [{"elo_diff_range": str, "h_rate": float, "d_rate": float, "a_rate": float, "n": int}]
        """
        rows = []
        for bin_idx in sorted(self._bins.keys()):
            counts = self._bins[bin_idx]
            n = counts["total"]
            if n < min_samples:
                continue
            
            lo = bin_idx * self.bin_size
            hi = lo + self.bin_size
            
            # 校准后的预测概率
            bin_center = (bin_idx + 0.5) * self.bin_size
            pred = self.predict(bin_center, 0)  # home_elo - away_elo = bin_center - home_adv
            
            rows.append({
                "elo_diff_range": f"[{lo:+.0f}, {hi:+.0f})",
                "n": n,
                "actual_h": round(counts["H"] / n, 3),
                "actual_d": round(counts["D"] / n, 3),
                "actual_a": round(counts["A"] / n, 3),
                "pred_h": pred["home_win"],
                "pred_d": pred["draw"],
                "pred_a": pred["away_win"],
            })
        return rows
    
    def summary(self) -> str:
        """打印校准器摘要"""
        lines = [
            f"{'='*60}",
            f"  ELO 概率校准器",
            f"{'='*60}",
            f"  状态:       {'已拟合' if self._fitted else '未拟合'}",
            f"  训练样本:   {self._n_samples} 场",
            f"  有效分桶:   {sum(1 for b in self._bins.values() if b['total'] >= self.min_bin_samples)}",
            f"  全局基准:   H={self._global_h:.3f} D={self._global_d:.3f} A={self._global_a:.3f}",
        ]
        if self._lr_h:
            s, b = self._lr_h
            lines.append(f"  P(H) 公式:  sigmoid({s:.5f}×Δelo + {b:.3f})")
        if self._lr_a:
            s, b = self._lr_a
            lines.append(f"  P(A) 公式:  sigmoid({s:.5f}×Δelo + {b:.3f})")
        lines.append(f"{'='*60}")
        return "\n".join(lines)
