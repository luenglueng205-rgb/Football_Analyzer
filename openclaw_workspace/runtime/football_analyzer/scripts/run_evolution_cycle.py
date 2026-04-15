import sys
import os
import asyncio
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.backtest_sandbox import BacktestSandbox
from agents.auto_tuner_agent import AutoTunerAgent

logging.basicConfig(level=logging.INFO, format='%(message)s')

# Mock 历史数据 (例如 2018 年世界杯的几场大热必死比赛)
MOCK_HISTORICAL_DATA = [
    {"home": "GER", "away": "KOR", "pre_match_odds": [1.15, 6.5, 15.0], "actual_result": "0"}, # 德国大热被爆冷
    {"home": "ARG", "away": "KSA", "pre_match_odds": [1.12, 7.0, 19.0], "actual_result": "0"}, # 阿根廷大热被爆冷
    {"home": "BRA", "away": "ICE", "pre_match_odds": [1.20, 5.5, 12.0], "actual_result": "1"}, # 巴西平局
    {"home": "FRA", "away": "CRC", "pre_match_odds": [1.30, 4.5, 8.0],  "actual_result": "3"}, # 法国正常打出
    {"home": "ENG", "away": "AUS", "pre_match_odds": [1.40, 4.0, 7.0],  "actual_result": "3"}  # 英格兰正常打出
]

async def main():
    print("\n🚀 [系统点火] 启动时光机与进化引擎...")
    
    # 1. 初始化沙盒并跑批测试
    sandbox = BacktestSandbox()
    report = sandbox.run_batch_simulation(MOCK_HISTORICAL_DATA)
    
    # 2. 将战报交给军师进行反思与变异
    tuner = AutoTunerAgent()
    await tuner.run_evolution_cycle(report)
    
if __name__ == "__main__":
    asyncio.run(main())
