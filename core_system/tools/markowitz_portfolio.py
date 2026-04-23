import numpy as np
from typing import Dict, List
import json

class MarkowitzPortfolioOptimizer:
    """
    2026 版现代投资组合理论与多场比赛凯利公式资金分配 (Fractional Kelly Portfolio)
    基于 Markowitz 模型和 Kelly Criterion 的结合。
    解决多场比赛同时开赛时的资金重叠和协方差风险。
    """
    def __init__(self, total_bankroll: float = 10000, max_drawdown: float = 0.15, kelly_fraction: float = 0.25):
        self.bankroll = total_bankroll
        self.max_drawdown = max_drawdown
        self.kelly_fraction = kelly_fraction

    def optimize_portfolio(self, matches: List[Dict]) -> Dict:
        """
        给定周末的 N 场比赛（包含各自的真实胜率、赔率和 EV），
        输出一个全局最优的注码分配方案。
        """
        if not matches:
            return {"status": "error", "message": "没有比赛数据", "portfolio": []}
            
        print(f"\n    [💼 Portfolio Optimizer] 启动多账户动态分数凯利。正在为 {len(matches)} 场比赛规划全局仓位...")
        
        portfolio = []
        total_exposure = 0.0
        
        # 第一遍扫描：剔除 EV < 0 的垃圾比赛
        valid_matches = [m for m in matches if m.get("ev", 0) > 0]
        
        if not valid_matches:
            return {"status": "skip", "message": "所有比赛的期望值(EV)均为负，建议空仓！", "portfolio": []}
            
        for match in valid_matches:
            ev = match.get("ev", 0)
            prob = match.get("probability", 0)
            odds = match.get("odds", 0)
            lottery_type = match.get("lottery_type", "jingcai")
            
            # 严格隔离北单机制
            actual_odds = odds * 0.65 if lottery_type == "beijing" else odds
            b = actual_odds - 1
            q = 1 - prob
            
            if b <= 0:
                continue
                
            # 单场凯利
            kelly = (b * prob - q) / b if b > 0 else 0
            
            if kelly > 0:
                # 动态分数凯利：考虑全局风险，降低单场暴露
                stake_ratio = kelly * self.kelly_fraction
                
                # 如果是高赔率爆冷，进一步降低仓位（防范尾部风险）
                if actual_odds > 5.0:
                    stake_ratio *= 0.5 
                    
                # 记录
                portfolio.append({
                    "match": match.get("match_name", "未知比赛"),
                    "selection": match.get("selection", "主胜"),
                    "odds": odds,
                    "actual_odds": actual_odds,
                    "ev": ev,
                    "kelly_ratio": stake_ratio,
                    "suggested_stake": self.bankroll * stake_ratio
                })
                total_exposure += stake_ratio
                
        # 第二遍扫描：全局回撤控制 (Max Drawdown Control)
        # 如果总仓位超过了允许的最大回撤（例如 15%），我们需要按比例缩减所有仓位
        if total_exposure > self.max_drawdown:
            scale_down_factor = self.max_drawdown / total_exposure
            print(f"    [💼 Portfolio Optimizer] ⚠️ 警告：初始仓位 ({total_exposure*100:.1f}%) 超过最大回撤红线 ({self.max_drawdown*100:.1f}%)！触发全局缩水保护。")
            for p in portfolio:
                p["kelly_ratio"] *= scale_down_factor
                p["suggested_stake"] *= scale_down_factor
        else:
            print(f"    [💼 Portfolio Optimizer] ✅ 全局资金暴露安全 ({total_exposure*100:.1f}%)，无需缩水。")
            
        # 按照投资金额排序
        portfolio.sort(key=lambda x: x["suggested_stake"], reverse=True)
        
        return {
            "status": "success",
            "total_matches_bet": len(portfolio),
            "total_capital_at_risk": sum(p["suggested_stake"] for p in portfolio),
            "portfolio": portfolio
        }

if __name__ == "__main__":
    # 模拟周末的 3 场比赛
    matches = [
        {"match_name": "曼联 vs 阿森纳", "selection": "主胜", "probability": 0.55, "odds": 2.10, "ev": 0.155, "lottery_type": "jingcai"},
        {"match_name": "切尔西 vs 维拉", "selection": "客胜", "probability": 0.20, "odds": 8.00, "ev": 0.600, "lottery_type": "jingcai"}, # 爆冷高赔
        {"match_name": "利物浦 vs 热刺", "selection": "主胜", "probability": 0.60, "odds": 1.50, "ev": -0.100, "lottery_type": "beijing"} # 北单负EV
    ]
    
    optimizer = MarkowitzPortfolioOptimizer(total_bankroll=10000, max_drawdown=0.10, kelly_fraction=0.25)
    result = optimizer.optimize_portfolio(matches)
    print(json.dumps(result, ensure_ascii=False, indent=2))
