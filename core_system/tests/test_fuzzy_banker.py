import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.parlay_rules_engine import ParlayRulesEngine

engine = ParlayRulesEngine()

# Test Case 1: 竞彩 自由过关 (选 8场, 全单选，打 4串1 和 5串1)
free_parlay_tickets = engine.generate_free_parlay_combinations([1]*8, [4, 5])
print(f"[竞彩自由过关-单选] 选8场，打4串1和5串1，总注数: {free_parlay_tickets}")

# Test Case 2: 竞彩 自由过关复式 (选 3场，第一场双选，第二场三选，第三场单选，打 2串1)
# 比赛A: 2选, 比赛B: 3选, 比赛C: 1选
# A+B = 2*3 = 6
# A+C = 2*1 = 2
# B+C = 3*1 = 3
# 总计 = 11注
complex_parlay_tickets = engine.generate_free_parlay_combinations([2, 3, 1], [2])
print(f"[竞彩自由过关-复式] 选3场(分别双选/三选/单选)，打2串1，总注数: {complex_parlay_tickets}")

# Test Case 3: 北京单场 模糊定胆 (选6场全单选，4串1过关，设3胆，要求至少命中2胆)
# 理论值：12注
fuzzy_tickets = engine.calculate_fuzzy_banker_combinations(
    banker_selections=[1, 1, 1],
    tuo_selections=[1, 1, 1],
    parlay_size=4,
    min_bankers=2
)
print(f"[北单模糊定胆-单选] 选6场，4串1过关，设3胆，至少命中2胆，总注数: {fuzzy_tickets}")

# Test Case 4: 竞彩 胆拖投注复式 (3个胆全单选，2个拖全双选，打 4串1)
# 竞彩胆拖必须包含所有胆(即3个胆)，所以拖只能选1个。
# 拖A双选，拖B双选。
# 注数 = 1(胆组合) * (拖A(2) + 拖B(2)) = 4注
jingcai_banker_tuo = engine.calculate_fuzzy_banker_combinations(
    banker_selections=[1, 1, 1],
    tuo_selections=[2, 2],
    parlay_size=4
    # min_bankers 默认为胆的数量 (3)
)
# Test Case 5: 传统足彩 任选九场 (选10场，2场双选，8场单选)
renjiu_tickets = engine.calculate_chuantong_combinations(
    match_selections=[2, 2, 1, 1, 1, 1, 1, 1, 1, 1],
    play_type="renjiu"
)
print(f"[传统足彩-任九] 选10场(2场双选，8场单选)，总注数: {renjiu_tickets}")

# Test Case 6: 传统足彩 14场胜负彩 (全单选)
sfc_tickets = engine.calculate_chuantong_combinations(
    match_selections=[1]*14,
    play_type="14_match"
)
print(f"[传统足彩-14场] 选14场(全单选)，总注数: {sfc_tickets}")

