import pytest
try:
    from openclaw_workspace.tools.parlay_filter_matrix import ParlayFilterMatrix
except ImportError:
    pytest.importorskip("standalone_workspace", reason="standalone_workspace 目录不存在，ParlayFilterMatrix 未实现")

def test_same_match_mutex():
    matrix = ParlayFilterMatrix()
    
    # 模拟从同一场比赛（match_id: 1001）选了胜平负和总进球
    candidates = [
        {"match_id": "1001", "selection": "HomeWin", "odds": 2.0, "market": "1x2"},
        {"match_id": "1001", "selection": "Over2.5", "odds": 1.9, "market": "total"},
        {"match_id": "1002", "selection": "AwayWin", "odds": 3.0, "market": "1x2"}
    ]
    
    # 测试：系统不应该生成包含两个 1001 的 2串1
    parlays = matrix.generate_parlays(candidates, parlay_type="2x1")
    
    for p in parlays:
        match_ids = [leg["match_id"] for leg in p["legs"]]
        # 如果列表中 match_id 数量不等于集合数量，说明有重复
        assert len(match_ids) == len(set(match_ids)), f"致命错误：生成了同场互斥的非法串关! {p}"
        
    # 我们期望生成的串关只有 (1001-HomeWin, 1002) 和 (1001-Over2.5, 1002)
    assert len(parlays) == 2

def test_max_payout_cap():
    matrix = ParlayFilterMatrix()
    
    # 模拟极其变态的高赔率，测试奖金封顶（2-3关最高 20万）
    candidates = [
        {"match_id": "2001", "selection": "Draw", "odds": 50.0, "market": "1x2"},
        {"match_id": "2002", "selection": "Draw", "odds": 50.0, "market": "1x2"}
    ]
    
    # 50 * 50 * 100本金 = 250,000 > 200,000 封顶
    parlays = matrix.generate_parlays(candidates, parlay_type="2x1", stake=100)
    
    assert parlays[0]["max_potential_return"] <= 200000, "致命错误：AI 给出了超过体彩中心物理上限的虚假奖金！"
    assert parlays[0]["max_potential_return"] == 200000

def test_calculate_parlay_mutex():
    matrix = ParlayFilterMatrix()
    
    # 直接计算已经包含同场比赛的组合应该被拒绝
    matches = [
        {"match_id": "1001", "selection": "HomeWin", "odds": 2.0},
        {"match_id": "1001", "selection": "Over2.5", "odds": 1.9}
    ]
    
    result = matrix.calculate_parlay(matches, parlay_type="2x1", total_stake=100)
    assert result["status"] == "error", "calculate_parlay 必须拒绝同场互斥的组合"
    assert "mutex" in result["message"].lower() or "同场" in result["message"]

def test_calculate_parlay_max_cap():
    matrix = ParlayFilterMatrix()
    
    # 模拟极其变态的高赔率，测试 calculate_parlay 的奖金封顶
    matches = [
        {"match_id": "2001", "selection": "Draw", "odds": 50.0},
        {"match_id": "2002", "selection": "Draw", "odds": 50.0}
    ]
    
    result = matrix.calculate_parlay(matches, parlay_type="2x1", total_stake=100)
    assert result["max_potential_return"] <= 200000, "calculate_parlay 没有应用奖金封顶限制"

def test_m_n_physical_decomposition():
    try:
        from openclaw_workspace.tools.parlay_rules_engine import ParlayRulesEngine
    except ImportError:
        pytest.skip("standalone_workspace/tools/parlay_rules_engine.py 不存在")
    engine = ParlayRulesEngine()
    
    # 3 matches, playing 3x4 (which means three 2x1 and one 3x1)
    legs = ["M1", "M2", "M3"]
    
    combos = engine.get_m_n_ticket_combinations(legs, 3, 4)
    
    assert len(combos) == 4
    assert ["M1", "M2"] in combos
    assert ["M1", "M3"] in combos
    assert ["M2", "M3"] in combos
    assert ["M1", "M2", "M3"] in combos

