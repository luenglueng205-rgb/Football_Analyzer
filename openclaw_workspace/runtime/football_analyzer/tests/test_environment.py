import pytest
from tools.environment_analyzer import EnvironmentAnalyzer

def test_environment_impact():
    analyzer = EnvironmentAnalyzer()
    
    base_home_xg = 1.5
    base_away_xg = 1.0
    
    # 模拟大雨天气，通常会导致总进球减少
    weather_data = {"condition": "heavy_rain", "temperature": 5}
    referee_data = {"cards_per_game": 5.5, "strictness": "high"}
    
    adj_home_xg, adj_away_xg = analyzer.calculate_impact(base_home_xg, base_away_xg, weather_data, referee_data)
    
    # 双方 xG 均应受大雨影响下降
    assert adj_home_xg < base_home_xg
    assert adj_away_xg < base_away_xg
