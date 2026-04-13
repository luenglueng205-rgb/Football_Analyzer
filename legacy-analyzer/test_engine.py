from skills.lottery_math_engine import LotteryMathEngine

print("测试竞彩舍入: 2 * 1.65 * 1.75 =", LotteryMathEngine.jingcai_round(2 * 1.65 * 1.75)) # 应为 5.78
print("测试竞彩舍入: 2 * 1.65 * 1.46 =", LotteryMathEngine.jingcai_round(2 * 1.65 * 1.46)) # 应为 4.82

res = LotteryMathEngine.calculate_jingcai_mxn(
    matches=[
        {"odds": [1.65], "play_type": "SPF"},
        {"odds": [1.75], "play_type": "SPF"},
        {"odds": [1.46], "play_type": "SPF"}
    ],
    m=3, n=4
)
print("测试竞彩 3串4:", res)

res_bd = LotteryMathEngine.calculate_beijing_single(
    matches=[
        {"odds": [3.0], "play_type": "SPF"},
        {"odds": [3.0], "play_type": "SPF"},
        {"odds": [3.0], "play_type": "SPF"},
        {"odds": [3.0], "play_type": "SPF"}
    ],
    m=4, n=1
)
print("测试北单 4串1 (sp全3.0):", res_bd) # prize = 2 * 3*3*3*3 * 0.65 = 105.3
