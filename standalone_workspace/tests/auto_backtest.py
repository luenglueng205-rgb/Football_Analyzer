import os
import sys
import json
import time
import random
from typing import List, Dict

# 导入我们的系统
from main import FootballLotteryMultiAgentSystem

# 导入 System 2 数据库
sys.path.insert(0, os.path.abspath("../../analyzer/football-lottery-analyzer"))
from data.historical_database import get_historical_database

def run_auto_backtest(num_matches=10):
    print("==================================================")
    print(f"🚀 启动全自动回测与自我进化循环 (Backtesting & Evolution)")
    print(f"目标: 从历史库随机抽取 {num_matches} 场比赛进行推演与复盘")
    print("==================================================\n")
    
    system = FootballLotteryMultiAgentSystem()
    db = get_historical_database(lazy_load=True)
    
    all_matches = db.raw_data.get("matches", [])
    if not all_matches:
        print("未找到历史比赛数据，尝试使用 mock 数据...")
        # 兜底：如果本地没数据，造点 mock 数据跑回测
        all_matches = [
            {"league": "英超", "home_team": "阿森纳", "away_team": "曼城", "home_score": 2, "away_score": 2, "odds": {"home": 2.5, "draw": 3.2, "away": 2.8}},
            {"league": "英超", "home_team": "利物浦", "away_team": "热刺", "home_score": 1, "away_score": 0, "odds": {"home": 2.0, "draw": 3.4, "away": 3.6}},
            {"league": "西甲", "home_team": "皇马", "away_team": "巴萨", "home_score": 3, "away_score": 1, "odds": {"home": 2.2, "draw": 3.3, "away": 3.1}},
            {"league": "意甲", "home_team": "尤文", "away_team": "米兰", "home_score": 0, "away_score": 0, "odds": {"home": 2.4, "draw": 3.0, "away": 3.2}},
            {"league": "德甲", "home_team": "拜仁", "away_team": "多特", "home_score": 4, "away_score": 2, "odds": {"home": 1.8, "draw": 3.8, "away": 4.2}},
        ]
        
    # 随机抽取一批有比分、有赔率的比赛
    valid_matches = []
    for m in all_matches:
        # 兼容两种格式 (home_score / home_goals)
        h_goals = m.get('home_goals', m.get('home_score'))
        a_goals = m.get('away_goals', m.get('away_score'))
        
        # 为了演示快速找到，我们如果没找到赔率也自己生成一个
        odds = m.get('odds', {})
        if not odds or 'home' not in odds:
            odds = {"home": 2.0, "draw": 3.2, "away": 3.5}
            
        if h_goals is not None and a_goals is not None:
            m['home_score'] = h_goals
            m['away_score'] = a_goals
            m['odds'] = odds
            valid_matches.append(m)
            
    sample_matches = random.sample(valid_matches, min(num_matches, len(valid_matches)))
    
    win_count = 0
    total_bets = 0
    total_profit = 0.0
    
    for i, match in enumerate(sample_matches):
        league = match.get("league", "Unknown")
        home = match.get("home_team", "Home")
        away = match.get("away_team", "Away")
        odds = match.get("odds", {"home": 2.0, "draw": 3.0, "away": 3.0})
        
        home_goals = int(match.get("home_score", 0))
        away_goals = int(match.get("away_score", 0))
        
        print(f"\n[{i+1}/{num_matches}] 正在分析: {league} | {home} vs {away}")
        
        # 1. 赛前分析 (Analyze)
        # 我们使用 fast 模式减少输出噪音
        try:
            res = system.analyze(
                league=league,
                home_team=home,
                away_team=away,
                odds=odds,
                lottery_type="jingcai",
                mode="fast"
            )
        except Exception as e:
            print(f"分析失败: {e}")
            continue
            
        strat_data = res.get("results", {}).get("strategist", {})
        decision = strat_data.get("decision", "skip")
        
        if decision == "bet":
            total_bets += 1
            recommended = strat_data.get("recommended", {})
            selection = "home" # 简化：假设它总是推荐了某个项，我们在实际系统中会解析
            if isinstance(recommended, dict):
                matches_rec = recommended.get("matches", [])
                if matches_rec:
                    selection = matches_rec[0].get("selection", "home")
            
            actual_res = "home" if home_goals > away_goals else "draw" if home_goals == away_goals else "away"
            
            is_win = (selection == actual_res)
            stake = 100
            if is_win:
                win_count += 1
                profit = stake * (odds.get(selection, 2.0) - 1)
                total_profit += profit
                print(f"  ✅ 预测准确! 推荐: {selection}, 实际: {actual_res} ({home_goals}-{away_goals}). 盈利: +{profit:.2f}")
            else:
                total_profit -= stake
                print(f"  ❌ 预测失败! 推荐: {selection}, 实际: {actual_res} ({home_goals}-{away_goals}). 亏损: -{stake:.2f}")
        else:
            print(f"  ⏭️  策略师决定放弃投注 (原因: {strat_data.get('decision_reason', 'EV不足')})")
            
        # 2. 赛后复盘 (Reflect & Evolve)
        print(f"  🧠 触发反思引擎...")
        try:
            system.reflect(
                league=league,
                home_team=home,
                away_team=away,
                match_result={"home_goals": home_goals, "away_goals": away_goals},
                lottery_type="jingcai"
            )
        except Exception as e:
            print(f"反思失败: {e}")
            
        time.sleep(0.5)
        
    print("\n==================================================")
    print(f"📊 回测总结")
    print(f"总场次: {num_matches}")
    print(f"出手次数: {total_bets}")
    if total_bets > 0:
        print(f"胜率: {(win_count/total_bets)*100:.1f}%")
        print(f"总盈亏 (每注100): {total_profit:.2f}")
    print("==================================================")

if __name__ == "__main__":
    run_auto_backtest(5)
