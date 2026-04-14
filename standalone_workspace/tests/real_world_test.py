import sys
import os
import json
from datetime import datetime

# 导入系统
sys.path.insert(0, os.path.abspath("."))
from main import FootballLotteryMultiAgentSystem

system = FootballLotteryMultiAgentSystem()

print("==================================================")
print("🚀 启动 TRAE LLM 深度实盘测试 (Real-World Test)")
print("==================================================\n")

matches = [
    {
        "league": "欧冠",
        "home_team": "皇马",
        "away_team": "曼城",
        "odds": {"home": 2.65, "draw": 3.40, "away": 2.45},
        "markets": {
            "handicap": {"line": 0, "home_odds": 1.95, "away_odds": 1.90}
        }
    },
    {
        "league": "英超",
        "home_team": "阿森纳",
        "away_team": "利物浦",
        "odds": {"home": 2.15, "draw": 3.50, "away": 3.10},
        "markets": {
            "handicap": {"line": -0.25, "home_odds": 1.85, "away_odds": 2.05}
        }
    },
    {
        "league": "欧联",
        "home_team": "勒沃库森",
        "away_team": "罗马",
        "odds": {"home": 1.95, "draw": 3.60, "away": 3.60},
        "markets": {
            "handicap": {"line": -0.5, "home_odds": 1.95, "away_odds": 1.90}
        }
    }
]

for m in matches:
    print(f"\n[{m['league']}] {m['home_team']} vs {m['away_team']}")
    print(f"初盘赔率: 主胜 {m['odds']['home']} | 平局 {m['odds']['draw']} | 客胜 {m['odds']['away']}")
    res = system.analyze(
        league=m['league'],
        home_team=m['home_team'],
        away_team=m['away_team'],
        odds=m['odds'],
        markets=m['markets'],
        lottery_type="jingcai",
        budget=1000,
        mode="full"
    )
    
    # 提取核心硬核数据供 LLM 读取
    analyst_data = res.get("results", {}).get("analyst", {})
    strat_data = res.get("results", {}).get("strategist", {})
    
    print("\n--- 核心底层数据 ---")
    print(f"1. 隐含概率: {json.dumps(analyst_data.get('probabilities'), ensure_ascii=False)}")
    print(f"2. 泊松进球预期: {json.dumps(analyst_data.get('professional_data', {}).get('poisson', {}).get('expected_goals'), ensure_ascii=False)}")
    
    # 提取亚指让球分析数据
    markets = analyst_data.get("markets", {})
    if "handicap" in markets and "probabilities" in markets["handicap"]:
        handicap_data = markets["handicap"]
        print(f"3. 亚指让球分析: 盘口 {handicap_data['line']}, 主胜率 {handicap_data['probabilities']['home_win']:.2%}, 客胜率 {handicap_data['probabilities']['away_win']:.2%}")
    
    print(f"4. 实时水位变动: {json.dumps(analyst_data.get('professional_data', {}).get('water_changes', {}), ensure_ascii=False)}")
    print(f"5. 策略生成: {json.dumps(strat_data.get('recommended'), ensure_ascii=False)}")
    
    # 提取风控凯利仓位
    risk_data = res.get("results", {}).get("risk_manager", {})
    if "checks" in risk_data and "kelly_bet" in risk_data["checks"]:
        kb = risk_data["checks"]["kelly_bet"]
        print(f"6. 凯利风控仓位: {kb.get('message', '')} (具体比例: {kb.get('optimal_bet_ratio', 0)*100:.2f}%)")
    
    print(f"7. 期望值(EV): {strat_data.get('expected_value')}")
    print("----------------------------------\n")

