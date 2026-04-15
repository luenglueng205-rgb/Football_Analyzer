from skills.lottery_math_engine import LotteryMathEngine

def test_engine():
    engine = LotteryMathEngine()
    
    # Test 1: Negative xG
    try:
        engine.calculate_all_markets(-1.0, 2.0)
        print("Test 1 Failed: ValueError not raised for negative xG")
    except ValueError as e:
        print(f"Test 1 Passed: {e}")
        
    # Test 2: Extreme xG
    try:
        res = engine.calculate_all_markets(20.0, 1.5)
        print("Test 2 Passed: Extreme xG handled correctly")
        print(f"Total probability sum (approx 1.0 expected): {sum(res['match_prob'].values())}")
    except Exception as e:
        print(f"Test 2 Failed: {e}")

if __name__ == '__main__':
    test_engine()
