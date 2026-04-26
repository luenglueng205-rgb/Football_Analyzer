import math
import json
import os
import asyncio
import sys
from scipy.optimize import root_scalar
from scipy.stats import poisson

# Add parent directory to sys.path to allow importing from skills and agents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from core_system.tools.math.lottery_math_engine import LotteryMathEngine
except ImportError:
    LotteryMathEngine = None

# Mock OS calls for demonstration
class SyndicateOS:
    def __init__(self):
        self.name = "SyndicateOS"

    def make_decision(self, home_xg, away_xg, all_markets):
        # A simple mock logic to decide based on xG
        total_xg = home_xg + away_xg
        if total_xg > 2.5:
            decision = f"推荐：竞彩总进球 大2.5球 (预期进球: {round(total_xg, 2)})"
        else:
            decision = f"推荐：竞彩总进球 小2.5球 (预期进球: {round(total_xg, 2)})"
        
        if home_xg > away_xg * 1.2:
            decision += "，主胜"
        elif away_xg > home_xg * 1.2:
            decision += "，客胜"
        else:
            decision += "，平局"
        return decision

def reverse_engineer_xg(home_odds: float, draw_odds: float, away_odds: float, juice: float = 0.05) -> tuple:
    """
    [修复版] 非线性泊松逆推：彻底抛弃粗糙的线性映射。
    利用 scipy.optimize.root_scalar 非线性求解器，强行逼近最精确的主客队预期进球 (xG)。
    """
    # 1. 去除抽水，获取庄家眼中的真实概率
    total_prob = (1/home_odds) + (1/draw_odds) + (1/away_odds)
    p_home_target = (1/home_odds) / total_prob
    p_away_target = (1/away_odds) / total_prob
    p_draw_target = (1/draw_odds) / total_prob
    
    # 2. 定义目标函数：寻找一个基础 xG，使得双泊松算出的胜率与真实概率最接近
    # 为了简化非线性方程组，我们假设总进球的基数 base_xg，并且主客队 xG 的比例与 p_home/p_away 的比例强相关
    ratio = p_home_target / p_away_target
    
    def objective_function(base_xg):
        # 根据 ratio 分配主客 xG
        h_xg = base_xg * (ratio / (1 + ratio)) * 2 # 乘以2是因为总进球是两队之和
        a_xg = base_xg * (1 / (1 + ratio)) * 2
        
        # 使用泊松分布计算 0-5 球的概率矩阵，求主胜概率
        calc_home_win = 0.0
        for h in range(1, 6):
            for a in range(0, h):
                calc_home_win += poisson.pmf(h, h_xg) * poisson.pmf(a, a_xg)
                
        # 目标：计算出的主胜概率 - 真实的 p_home_target = 0
        return calc_home_win - p_home_target
        
    try:
        # 使用 scipy.optimize 寻找根 (root)，假设一场比赛总进球在 0.5 到 5.5 之间
        result = root_scalar(objective_function, bracket=[0.5, 5.5], method='brentq')
        if result.converged:
            optimal_base_xg = result.root
            h_xg = optimal_base_xg * (ratio / (1 + ratio)) * 2
            a_xg = optimal_base_xg * (1 / (1 + ratio)) * 2
            return round(h_xg, 2), round(a_xg, 2)
    except ValueError:
        # 如果非线性求解失败（例如赔率极度悬殊，找不到根），回退到粗糙的线性映射
        pass
        
    # Fallback 机制
    base_xg = 2.5
    home_xg = base_xg * p_home_target * 1.2
    away_xg = base_xg * p_away_target
    return max(0.1, round(home_xg, 2)), max(0.1, round(away_xg, 2))

async def run_backtest(sample_size: int = 5):
    print("==================================================")
    print("🕰️ [时光机] 终极历史回测沙盒启动")
    print("==================================================")
    
    # 1. 加载历史数据
    data_path = os.path.join(os.path.dirname(__file__), "..", "..", "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json")
    if not os.path.exists(data_path):
        print(f"警告: 找不到历史数据文件 {data_path}，使用模拟数据进行演示。")
        matches = [
            {
                "date": "2023-10-01", "league": "英超", "home_team": "阿森纳", "away_team": "曼城",
                "home_odds": 2.80, "draw_odds": 3.40, "away_odds": 2.40,
                "home_goals": 1, "away_goals": 0
            },
            {
                "date": "2023-10-02", "league": "西甲", "home_team": "皇马", "away_team": "巴萨",
                "home_odds": 2.10, "draw_odds": 3.50, "away_odds": 3.20,
                "home_goals": 2, "away_goals": 2
            }
        ]
    else:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        matches = data.get("matches", [])[-sample_size:] # 取最后几场测试
        
    try:
        if LotteryMathEngine:
            math_engine = LotteryMathEngine()
        else:
            math_engine = None
    except Exception as e:
        print(f"警告: 初始化 LotteryMathEngine 失败: {e}，将跳过 calculate_all_markets")
        math_engine = None

    os_system = SyndicateOS()
    
    for match in matches:
        print(f"\n▶ 正在回测: {match['date']} | {match['league']} | {match['home_team']} vs {match['away_team']}")
        print(f"  历史初赔: {match['home_odds']} / {match['draw_odds']} / {match['away_odds']}")
        
        # 2. 泊松逆向重构
        home_xg, away_xg = reverse_engineer_xg(
            float(match['home_odds']), 
            float(match['draw_odds']), 
            float(match['away_odds'])
        )
        print(f"  逆向推演 xG: 主 {home_xg} - 客 {away_xg}")
        
        # 生成体彩全景赔率
        all_markets = {}
        if math_engine and hasattr(math_engine, 'calculate_all_markets'):
            try:
                all_markets = math_engine.calculate_all_markets(home_xg, away_xg, handicap=-1)
                print(f"  已生成体彩全景赔率: 包含 {len(all_markets)} 种玩法")
            except Exception as e:
                print(f"  生成体彩全景赔率时出错: {e}")
        else:
            print("  (跳过真实 LotteryMathEngine 计算，使用空的全景赔率字典)")
        
        # 3. 虚拟决策
        print("  唤醒 SyndicateOS 进行决策 (由于是回测，跳过真实 API 抓取，直接注入重构赔率)...")
        decision = os_system.make_decision(home_xg, away_xg, all_markets)
        
        # 4. 对账
        actual_score = f"{match['home_goals']}-{match['away_goals']}"
        print(f"  ✅ 历史真实赛果: {actual_score}")
        print(f"  🤖 AI 虚拟决策: {decision}")
        
        # check if decision matches actual
        actual_total = int(match['home_goals']) + int(match['away_goals'])
        actual_is_over = actual_total > 2.5
        pred_is_over = (home_xg + away_xg) > 2.5
        
        actual_res = "主胜" if match['home_goals'] > match['away_goals'] else ("客胜" if match['home_goals'] < match['away_goals'] else "平局")
        pred_res = "主胜" if home_xg > away_xg * 1.2 else ("客胜" if away_xg > home_xg * 1.2 else "平局")
        
        match_status = "🎯 命中!" if (actual_is_over == pred_is_over) and (actual_res == pred_res) else ("⚠️ 部分命中" if actual_is_over == pred_is_over or actual_res == pred_res else "❌ 未命中")
        print(f"  📊 对账结果: {match_status}")
        
        print("  --------------------------------------------------")

if __name__ == "__main__":
    asyncio.run(run_backtest())
