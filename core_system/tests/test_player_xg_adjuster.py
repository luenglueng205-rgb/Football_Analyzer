import pytest
from tools.player_xg_adjuster import PlayerXgAdjuster

def test_adjust_xg_for_key_player_injury():
    adjuster = PlayerXgAdjuster()
    
    # 模拟德布劳内伤停，战术权重极高
    base_xg = 2.0
    injuries = [{"name": "Kevin De Bruyne", "role": "playmaker", "importance": 0.9}]
    
    adjusted_xg = adjuster.calculate_adjusted_xg(base_xg, injuries)
    
    # 预期 xG 会因为核心球员伤停而下调约 10-15%
    assert adjusted_xg < base_xg
    assert adjusted_xg > 1.5
    assert round(adjusted_xg, 2) == 1.73 # 假设公式为 base * (1 - importance * 0.15)
