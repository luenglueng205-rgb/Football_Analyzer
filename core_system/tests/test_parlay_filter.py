from tools.parlay_filter_matrix import ParlayFilterMatrix

def test_parlay_2x1_calculation():
    matrix = ParlayFilterMatrix()
    matches = [
        {"match_id": "001", "selection": "主胜", "odds": 2.0},
        {"match_id": "002", "selection": "客胜", "odds": 3.0}
    ]
    
    result = matrix.calculate_parlay(matches, parlay_type="2x1", total_stake=100)
    
    assert result["status"] == "success"
    assert result["total_cost"] == 100
    assert result["combinations"][0]["combined_odds"] == 6.0
    assert result["max_potential_return"] == 600.0

def test_parlay_3x4_calculation():
    matrix = ParlayFilterMatrix()
    matches = [
        {"match_id": "001", "selection": "主胜", "odds": 2.0},
        {"match_id": "002", "selection": "大球", "odds": 1.5},
        {"match_id": "003", "selection": "平局", "odds": 3.2}
    ]
    
    # 3x4 means three 2x1s and one 3x1 (4 bets total)
    result = matrix.calculate_parlay(matches, parlay_type="3x4", total_stake=400)
    
    assert result["status"] == "success"
    assert result["total_cost"] == 400
    assert len(result["combinations"]) == 4

if __name__ == "__main__":
    test_parlay_2x1_calculation()
    test_parlay_3x4_calculation()
    print("Parlay filter tests PASSED")
