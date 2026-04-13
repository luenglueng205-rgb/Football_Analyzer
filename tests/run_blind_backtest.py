import json
import random
from typing import List, Dict
import sys
import os

# 导入我们的原子工具和底层引擎
sys.path.insert(0, os.path.abspath("../../analyzer/football-lottery-analyzer"))
from tools.atomic_skills import calculate_poisson_probability, evaluate_betting_value
from data.historical_database import get_historical_database

print("==================================================")
print("📈 真实历史数据盲测 (Blind Backtesting) 启动")
print("==================================================\n")

db = get_historical_database(lazy_load=False)
jingcai_data = db.chinese_data.get("竞彩足球", {})
matches = jingcai_data.get("matches", [])

if not matches:
    print("未找到竞彩足球历史数据，请检查 data/chinese_mapped 目录。")
    sys.exit(1)

# 过滤出近几年的比赛，确保赔率数据完整
recent_matches = [m for m in matches if m.get("比赛日期", "") >= "2023-01-01" and m.get("主队赔率")]

# 随机挑选一个比赛日进行“盲测”
target_date = random.choice(recent_matches)["比赛日期"]
print(f"🎯 随机锁定测试日期: {target_date}")

day_matches = [m for m in recent_matches if m["比赛日期"] == target_date]
print(f"📊 当日共有 {len(day_matches)} 场竞彩赛事在售。")

# 模拟投注记录
bets_placed = []
total_investment = 0
total_return = 0

print("\n🤖 Agent 正在进行全盘扫描与 EV 计算 (隐藏真实赛果)...\n")

for m in day_matches:
    home = m["主队"]
    away = m["客队"]
    league = m["联赛中文名"]
    
    odds_h = m["主队赔率"]
    odds_d = m["平局赔率"]
    odds_a = m["客队赔率"]
    
    # 1. 真实历史特征提取 (使用 historical_database 计算真实的 mu)
    h_stats = db.get_team_stats(home)
    a_stats = db.get_team_stats(away)
    
    # 如果找不到球队历史数据，给予默认值 1.3
    mu_home = h_stats.get("avg_goals_scored", 1.3) if h_stats else 1.3
    mu_away = a_stats.get("avg_goals_scored", 1.0) if a_stats else 1.0
    
    # 加入主场优势微调
    mu_home *= 1.1 
    
    # 2. 调用泊松原子工具算真实概率
    poisson_res = json.loads(calculate_poisson_probability(mu_home, mu_away, 0.0))
    prob_h = poisson_res["1x2_probabilities"]["home_win"]
    prob_d = poisson_res["1x2_probabilities"]["draw"]
    prob_a = poisson_res["1x2_probabilities"]["away_win"]
    
    # 3. 扫描 EV (寻找价值洼地)
    ev_h = json.loads(evaluate_betting_value(prob_h, odds_h, 0.0, "jingcai"))
    ev_d = json.loads(evaluate_betting_value(prob_d, odds_d, 0.0, "jingcai"))
    ev_a = json.loads(evaluate_betting_value(prob_a, odds_a, 0.0, "jingcai"))
    
    # 寻找最高 EV
    best_ev = max(ev_h["expected_value"], ev_d["expected_value"], ev_a["expected_value"])
    
    # 只有 EV > 0 才值得下注 (由于竞彩抽水高，我们稍微放宽到 EV > -0.05 视为可搏)
    if best_ev > -0.05:
        # 决定买什么
        if best_ev == ev_h["expected_value"]:
            pick = "主胜"
            odds = odds_h
            prob = prob_h
        elif best_ev == ev_d["expected_value"]:
            pick = "平局"
            odds = odds_d
            prob = prob_d
        else:
            pick = "客胜"
            odds = odds_a
            prob = prob_a
            
        # 假设每次下注 100 元
        stake = 100
        total_investment += stake
        
        # 记录下注
        bets_placed.append({
            "match": f"[{league}] {home} vs {away}",
            "pick": pick,
            "odds": odds,
            "prob": prob,
            "ev": best_ev,
            "actual_h_goals": m["主队进球"],
            "actual_a_goals": m["客队进球"]
        })

print("==================================================")
print("揭晓真实赛果与投资回报 (ROI)")
print("==================================================")

if not bets_placed:
    print("Agent 判断今日所有比赛均无投注价值 (EV极低)，成功管住了手！")
else:
    for b in bets_placed:
        actual_h = b["actual_h_goals"]
        actual_a = b["actual_a_goals"]
        
        # 判断实际赛果
        if actual_h > actual_a: actual_res = "主胜"
        elif actual_h == actual_a: actual_res = "平局"
        else: actual_res = "客胜"
        
        # 判断是否中奖
        if b["pick"] == actual_res:
            won = True
            payout = 100 * b["odds"]
            total_return += payout
            status = f"✅ 中奖! (+{payout-100:.2f}元)"
        else:
            won = False
            status = f"❌ 未中 (-100元)"
            
        print(f"{b['match']} | 模型预测: {b['pick']} (赔率 {b['odds']}) | 实际比分: {actual_h}:{actual_a} ({actual_res}) | {status}")

    print("\n--------------------------------------------------")
    print(f"总投入: {total_investment:.2f} 元")
    print(f"总返还: {total_return:.2f} 元")
    profit = total_return - total_investment
    roi = (profit / total_investment) * 100
    print(f"净利润: {profit:.2f} 元")
    print(f"ROI (投资回报率): {roi:.2f}%")
