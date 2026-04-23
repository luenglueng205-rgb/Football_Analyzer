from tools.asian_handicap_analyzer import AsianHandicapAnalyzer

def test_euro_asian_divergence():
    analyzer = AsianHandicapAnalyzer()
    
    # Euro odds 1.50 typically implies Asian Handicap -1.0
    # If actual AH is -0.75, it's a shallow trap.
    result = analyzer.analyze_divergence(
        euro_home_odds=1.50,
        actual_asian_handicap=-0.75,
        home_water=0.85
    )
    
    assert result["theoretical_handicap"] == -1.0
    assert result["divergence"] == 0.25
    assert result["conclusion"] == "Shallow Trap (诱盘/阻筹)"
    
def test_water_drop():
    analyzer = AsianHandicapAnalyzer()
    result = analyzer.analyze_water_drop(
        opening_water=1.05,
        live_water=0.80
    )
    assert result["drop_amplitude"] == 0.25
    assert result["is_sharp_drop"] == True

if __name__ == "__main__":
    test_euro_asian_divergence()
    test_water_drop()
    print("Asian handicap tests PASSED")
