import sys
import os
import json
import pytest
sys.path.insert(0, os.path.abspath("."))
try:
    from main import FootballLotteryMultiAgentSystem
except ImportError:
    pytest.importorskip("main", reason="main.py 模块不存在（FootballLotteryMultiAgentSystem 未实现）")

system = FootballLotteryMultiAgentSystem()

# Test Jingcai M串N (3 matches)
matches_jingcai = [
    {"odds": {"home": 1.8, "draw": 3.1, "away": 4.0}},
    {"odds": {"home": 2.1, "draw": 3.0, "away": 3.2}},
    {"odds": {"home": 1.5, "draw": 3.8, "away": 5.5}}
]

print("=== 测试竞彩串关 ===")
res_jc = system.analyze(
    league="英超",
    home_team="TeamA",
    away_team="TeamB",
    matches=matches_jingcai,
    budget=100,
    lottery_type="jingcai",
    mode="full"
)
print(system._format_result(res_jc))

# Test Traditional RX9 (14 matches)
matches_14 = []
for i in range(14):
    matches_14.append({"主队": f"Home{i}", "客队": f"Away{i}", "odds": {"home": 2.0}})

print("\n=== 测试传统任九 ===")
res_rx9 = system.analyze(
    league="英超",
    home_team="Home0",
    away_team="Away0",
    matches=matches_14,
    budget=200,
    lottery_type="traditional",
    mode="full"
)
print(system._format_result(res_rx9))
