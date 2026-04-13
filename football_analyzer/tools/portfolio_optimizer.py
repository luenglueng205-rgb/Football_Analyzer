import json
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PortfolioOptimizer:
    """
    同步凯利与马科维茨风险平价 (Simultaneous Kelly & Risk Parity)。
    针对多场并发比赛 (Multi-Bet Portfolio) 的资金仓位管理。
    解决孤立投注导致的单日破产风险。
    """
    
    def __init__(self, max_total_exposure: float = 0.15):
        self.max_total_exposure = max_total_exposure # 单日总暴露度不可超过 15%

    def optimize_simultaneous_kelly(self, bets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        核心方法：同步凯利公式 (多重独立事件)
        :param bets: 潜在价值投注列表 [{"match_id": "A", "prob": 0.6, "odds": 2.0}]
        """
        total_fraction = 0.0
        optimized_bets = []
        
        # 1. 过滤 -EV 订单
        positive_ev_bets = []
        for bet in bets:
            prob = bet.get("prob", 0.0)
            odds = bet.get("odds", 0.0)
            ev = prob * odds - 1
            if ev > 0:
                positive_ev_bets.append({"bet": bet, "ev": ev, "b": odds - 1, "p": prob, "q": 1 - prob})
                
        # 2. 如果没有价值投注
        if not positive_ev_bets:
            return {"total_exposure": 0.0, "portfolio": [], "llm_semantic_reasoning": "全盘无 +EV (正期望) 投注，建议空仓。"}
            
        # 3. 简化版多事件同步凯利计算 (假定独立事件)
        # 实战中若是同组比赛还需协方差矩阵对冲
        for pb in positive_ev_bets:
            # 单场全仓凯利
            k = (pb["p"] * pb["b"] - pb["q"]) / pb["b"]
            # 引入半凯利 (Half-Kelly) 以平滑回撤
            half_k = max(0.0, k * 0.5)
            pb["recommended_fraction"] = half_k
            total_fraction += half_k
            
        # 4. 强制缩放 (Risk Parity) 控制最大回撤上限
        scale_factor = 1.0
        if total_fraction > self.max_total_exposure:
            scale_factor = self.max_total_exposure / total_fraction
            
        for pb in positive_ev_bets:
            final_f = pb["recommended_fraction"] * scale_factor
            optimized_bets.append({
                "match_id": pb["bet"].get("match_id", "Unknown"),
                "ev": round(pb["ev"], 4),
                "allocated_bankroll_pct": round(final_f, 4),
                "amount_per_10k": round(final_f * 10000, 2) # 以 1万 资金为例的投注额
            })
            
        actual_total_exposure = sum([b["allocated_bankroll_pct"] for b in optimized_bets])
        
        semantic_reasoning = f"【同步凯利资产组合】"
        semantic_reasoning += f" 发现 {len(positive_ev_bets)} 个正期望选项。为避免单日黑天鹅破产，"
        if scale_factor < 1.0:
            semantic_reasoning += f" 原始总暴露度达 {round(total_fraction*100)}%，已强制压缩至 {round(actual_total_exposure*100)}% 安全红线内。请按列表中的比例严格分仓。"
        else:
            semantic_reasoning += f" 总暴露度 {round(actual_total_exposure*100)}% 处于安全线内，已分配至各单场最优比例。"

        return {
            "total_exposure": round(actual_total_exposure, 4),
            "portfolio": sorted(optimized_bets, key=lambda x: x["allocated_bankroll_pct"], reverse=True),
            "llm_semantic_reasoning": semantic_reasoning
        }

def optimize_multi_match_portfolio(bets: List[Dict[str, Any]]) -> str:
    logger.info(f"执行同步凯利与组合优化 (Simultaneous Kelly Portfolio) ...")
    optimizer = PortfolioOptimizer()
    res = optimizer.optimize_simultaneous_kelly(bets)
    return json.dumps(res, ensure_ascii=False)

if __name__ == "__main__":
    # 测试：三场超高胜率比赛并发 (如果不做缩放，很容易梭哈导致爆仓)
    bets_pool = [
        {"match_id": "M1", "prob": 0.8, "odds": 1.5},
        {"match_id": "M2", "prob": 0.7, "odds": 1.8},
        {"match_id": "M3", "prob": 0.6, "odds": 2.5}
    ]
    print(optimize_multi_match_portfolio(bets_pool))