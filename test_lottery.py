from standalone_workspace.skills.lottery_math_engine import LotteryMathEngine

engine = LotteryMathEngine()
try:
    engine.calculate_all_markets(-1.0, 2.0)
    print("Failed: No ValueError on negative xG")
except ValueError as e:
    print(f"Success: Caught negative xG ({e})")

res = engine.calculate_all_markets(20.0, 1.0)
print(f"Success: Large xG processed, dynamic matrix expanded.")
print(f"Total Goals '7+': {res['total_goals']['7+']}")
