import pytest
import sys
import os

# Ensure the standalone_workspace directory is in sys.path so we can import skills
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from skills.lottery_math_engine import LotteryMathEngine

def test_extreme_xg_values():
    engine = LotteryMathEngine()
    
    # 测试 1: xG 为 0 的情况（不应抛出除零或域错误，应该返回 0-0 概率 100%）
    markets_zero = engine.calculate_all_markets(0.0, 0.0)
    assert markets_zero["total_goals"]["0"] > 0.99
    
    # 测试 2: 负数 xG 的情况（理论上 xG 不能为负，系统应兜底处理或抛出明确异常，而不是静默计算错误）
    with pytest.raises((ValueError, AssertionError)) as excinfo:
        engine.calculate_all_markets(-1.0, 2.0)
    
    # 测试 3: 极大 xG（如 20.0，测试计算性能和内存是否溢出，概率是否收敛）
    markets_huge = engine.calculate_all_markets(20.0, 1.0)
    assert markets_huge["match_prob"]["Win"] > 0.99

def test_universal_16_play_settlement():
    from tools.settlement_engine import SettlementEngine
    engine = SettlementEngine()
    
    # HT 0-1, FT 2-1
    result = engine.determine_all_play_types_results("2-1", "0-1", {"JINGCAI_HANDICAP": -1, "BEIDAN_HANDICAP": -0.5})
    
    assert result["status"] == "SETTLED"
    assert result["WDL"] == "3"
    assert result["JINGCAI_HANDICAP_WDL"] == "1" # 2 - 1 - 1 = 0 (Draw)
    assert result["BEIDAN_HANDICAP_WDL"] == "3" # 2 - 0.5 = 1.5 > 1 (Win)
    assert result["GOALS"] == "3"
    assert result["CS"] == "2-1"
    assert result["HTFT"] == "0-3"
    assert result["UP_DOWN_ODD_EVEN"] == "UP_ODD" # 3 goals (>=3 is UP), Odd

