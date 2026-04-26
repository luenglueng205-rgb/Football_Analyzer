import os
import sys

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

from standalone_workspace.tools.markowitz_portfolio import MarkowitzPortfolioOptimizer

def run_saturday_portfolio():
    print("==================================================")
    print("📈 [Markowitz Portfolio] 周末多场次资金分配优化启动")
    print("==================================================")
    
    # 模拟周末 6 场比赛经过大模型和图网络筛选后，全部为正 EV 的候选池
    candidates = [
        {"match_name": "EPL_01", "selection": "home_win", "odds": 1.90, "probability": 0.60, "ev": 1.14},
        {"match_name": "EPL_02", "selection": "away_win", "odds": 2.50, "probability": 0.45, "ev": 1.125},
        {"match_name": "LA_01",  "selection": "draw",     "odds": 3.40, "probability": 0.32, "ev": 1.088},
        {"match_name": "SA_01",  "selection": "home_win", "odds": 1.50, "probability": 0.72, "ev": 1.08},
        {"match_name": "UCL_01", "selection": "away_win", "odds": 4.20, "probability": 0.28, "ev": 1.176}, # 高赔防冷
        {"match_name": "UCL_02", "selection": "draw",     "odds": 3.60, "probability": 0.35, "ev": 1.26},  # 高赔防冷
        {"match_name": "UCL_03", "selection": "home_win", "odds": 2.10, "probability": 0.55, "ev": 1.155}, # 触发回撤红线的比赛
    ]
    
    print(f"-> 发现 {len(candidates)} 场正期望(EV>1)赛事，准备进行马科维茨风险平价计算...")
    
    total_bankroll = 10000.0
    optimizer = MarkowitzPortfolioOptimizer(total_bankroll=total_bankroll, max_drawdown=0.15) # 最大单日回撤 15%
    
    result = optimizer.optimize_portfolio(candidates)
    
    if result["status"] == "success":
        portfolio = result["portfolio"]
        print("\n✅ 资金分配矩阵计算完成：")
        for bet in portfolio:
            print(f"   赛事: {bet['match']} | 选项: {bet['selection']} | 赔率: {bet['odds']} | "
                  f"分配资金: ${bet['suggested_stake']:.2f} ({bet['kelly_ratio']*100:.2f}% 仓位)")
                  
        total_exposure = result["total_capital_at_risk"]
        print(f"\n📊 投资组合统计：")
        print(f"   总本金: ${total_bankroll:.2f}")
        print(f"   总暴露资金: ${total_exposure:.2f} (占比: {(total_exposure/total_bankroll)*100:.2f}%)")
    else:
        print(f"❌ 计算失败或全部跳过: {result.get('message')}")

if __name__ == "__main__":
    run_saturday_portfolio()