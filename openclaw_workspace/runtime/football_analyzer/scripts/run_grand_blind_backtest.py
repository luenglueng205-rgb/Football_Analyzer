import asyncio
import logging
import sys
import os
import json
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.backtest_sandbox import BacktestSandbox
from agents.auto_tuner_agent import AutoTunerAgent

logging.basicConfig(level=logging.INFO, format='%(message)s')

def generate_mock_historical_month() -> list:
    """
    生成 100 场高度仿真的 2025 年 1 月历史赛事，用于盲测。
    包含正常打出的低赔率、诱盘的高赔率、以及各种冷门。
    """
    matches = []
    teams = ["MCI", "ARS", "LIV", "CHE", "TOT", "MUN", "NEW", "WHU", "AVL", "BHA"]
    
    for i in range(100):
        home = random.choice(teams)
        away = random.choice([t for t in teams if t != home])
        
        # 随机生成赔率形态
        scenario = random.choices(["STRONG_HOME", "BALANCED", "AWAY_FAV"], weights=[0.5, 0.3, 0.2])[0]
        
        if scenario == "STRONG_HOME":
            home_odds = round(random.uniform(1.10, 1.60), 2)
            draw_odds = round(random.uniform(4.0, 6.0), 2)
            away_odds = round(random.uniform(7.0, 15.0), 2)
            # 强队 80% 赢，20% 爆冷
            actual = "3" if random.random() < 0.8 else random.choice(["1", "0"])
        elif scenario == "BALANCED":
            home_odds = round(random.uniform(2.10, 2.80), 2)
            draw_odds = round(random.uniform(3.0, 3.5), 2)
            away_odds = round(random.uniform(2.50, 3.20), 2)
            # 胶着比赛
            actual = random.choices(["3", "1", "0"], weights=[0.4, 0.3, 0.3])[0]
        else:
            home_odds = round(random.uniform(4.0, 8.0), 2)
            draw_odds = round(random.uniform(3.5, 4.5), 2)
            away_odds = round(random.uniform(1.30, 1.80), 2)
            # 客场强队 75% 赢，25% 爆冷
            actual = "0" if random.random() < 0.75 else random.choice(["3", "1"])
            
        matches.append({
            "home": home,
            "away": away,
            "pre_match_odds": [home_odds, draw_odds, away_odds],
            "actual_result": actual
        })
        
    return matches

async def run_blind_backtest():
    print("\n" + "="*60)
    print("⏳ [第一阶段] 启动无监控盲测回测 (Blind Backtest Run) ⏳")
    print("="*60)
    
    print(">> 系统正在提取 2025 年 1 月的 100 场全量赛事特征 (屏蔽真实赛果)...")
    historical_matches = generate_mock_historical_month()
    
    sandbox = BacktestSandbox()
    
    print("\n>> 🧠 军师开始看盘出票 (基于当前出厂基因权重)...")
    report = sandbox.run_batch_simulation(historical_matches)
    
    print("\n" + "="*60)
    print("🧬 [第二阶段] 激活首轮大进化 (The First Grand Evolution) 🧬")
    print("="*60)
    
    print(">> 军师正在深夜复盘这 100 场赛事的盈亏财报...")
    tuner = AutoTunerAgent()
    await tuner.run_evolution_cycle(report)

if __name__ == "__main__":
    asyncio.run(run_blind_backtest())
