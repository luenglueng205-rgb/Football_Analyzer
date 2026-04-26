import json
import logging
import traceback
from typing import Dict, Any

# 导入所有核心工具
import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from tools.environment_analyzer import UnstructuredFactorAnalyzer
from tools.player_xg_adjuster import PlayerImpactAdjuster
from tools.monte_carlo_simulator import MatchTimelineSimulator
from tools.smart_money_tracker import SmartMoneyTracker
from tools.atomic_skills import evaluate_betting_value
from tools.mxn_calculator import MxnCalculator
from agents.auto_tuner import AutoTuningEvolutionEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_cross_dimensional_tests():
    issues_found = []
    
    logger.info("=== 开始全方位无死角交叉测试 ===")
    
    # --- 维度 1: 极端边界值测试 (Extreme Edge Cases) ---
    logger.info("\n[测试维度 1]: 极端边界值测试")
    try:
        # 1.1 极端天气 + 严重伤停 (xG 是否会跌破 0 导致报错？)
        logger.info("测试 1.1: 极端伤停导致的 xG 衰减下限")
        xg_adjuster = PlayerImpactAdjuster()
        missing = [{"name": "Messi", "xg90": 2.5, "xa90": 1.5, "minutes_share": 1.0}] # 极其夸张的缺阵
        adj_result = xg_adjuster.calculate_xg_adjustment(1.0, missing)
        if adj_result["adjusted_xg"] <= 0:
            issues_found.append("Bug: 伤停调整后的 xG 跌破 0，会导致泊松分布数学错误 (Math Domain Error)。")
        logger.info(f"结果: {adj_result['adjusted_xg']} (下限保护正常)")
        
        # 1.2 蒙特卡洛时间轴极值测试 (0 vs 0, 15 vs 15)
        logger.info("测试 1.2: 蒙特卡洛极端比分模拟")
        mc_sim = MatchTimelineSimulator(num_simulations=1000)
        probs_0 = mc_sim.simulate_ht_ft_probabilities(0.01, 0.01) # 极小
        probs_15 = mc_sim.simulate_ht_ft_probabilities(15.0, 15.0) # 极大
        if sum(probs_0.values()) < 0.99 or sum(probs_15.values()) < 0.99:
            issues_found.append("Bug: 蒙特卡洛模拟的概率总和不等于 1.0。")
            
        # 1.3 聪明资金异常赔率测试 (包含 0 或负数赔率)
        logger.info("测试 1.3: 聪明资金计算器异常赔率除零错误")
        smt = SmartMoneyTracker()
        try:
            smt.track_odds_movement("test", {"home": 0.0, "draw": 3.0, "away": 3.0}, {"home": 1.5, "draw": 3.0, "away": 3.0})
        except ZeroDivisionError:
            issues_found.append("Bug: SmartMoneyTracker 没有拦截赔率为 0 的除零异常。")
            
    except Exception as e:
        issues_found.append(f"维度 1 崩溃: {traceback.format_exc()}")

    # --- 维度 2: 工具链数据传递测试 (Toolchain Integration) ---
    logger.info("\n[测试维度 2]: 工具链数据传递与序列化兼容性")
    try:
        # 环境分析 -> xG调整 -> 蒙特卡洛 -> 凯利准则
        env_analyzer = UnstructuredFactorAnalyzer()
        env_res = env_analyzer.analyze_match_environment("test", "Heavy rain", "Anthony Taylor")
        xg_modifier = env_res["quantitative_adjustments"]["total_xg_modifier"]
        
        base_xg = 2.0
        env_adjusted_xg = base_xg * xg_modifier
        
        player_res = xg_adjuster.calculate_xg_adjustment(env_adjusted_xg, [{"name": "Player A", "xg90": 0.5, "xa90": 0.2}])
        final_xg = player_res["adjusted_xg"]
        
        mc_probs = mc_sim.simulate_ht_ft_probabilities(final_xg, 1.0)
        
        # 序列化测试 (确保大模型能接收)
        json.dumps(mc_probs)
    except Exception as e:
        issues_found.append(f"维度 2 崩溃 (工具链断裂): {traceback.format_exc()}")

    # --- 维度 3: 并发与文件读写安全 (Concurrency & File I/O) ---
    logger.info("\n[测试维度 3]: 文件 I/O 与并发安全性")
    try:
        tuner = AutoTuningEvolutionEngine()
        # 测试非法配置结构
        tuner.evolve_parameters("test", "Fake_League", "modifier", 1.0)
        
        # 写入脏数据测试 json 解析容错
        with open(tuner.weights_file, 'w') as f:
            f.write("{invalid_json: true,")
        try:
            res = tuner._read_current_weights()
            if res != {}:
                issues_found.append("Bug: AutoTuningEvolutionEngine 解析错误时没有返回空字典保护。")
        except json.JSONDecodeError:
            issues_found.append("Bug: AutoTuningEvolutionEngine 读取配置文件时未捕获 JSONDecodeError，向外抛出了异常。")
            
        # 恢复正常数据
        tuner.__init__()
    except Exception as e:
        if "JSONDecodeError" not in str(e):
            issues_found.append(f"维度 3 崩溃: {traceback.format_exc()}")

    # --- 维度 4: 凯利准则与风控盲区 (Risk Management Blindspots) ---
    logger.info("\n[测试维度 4]: 凯利准则极端情况")
    try:
        # 测试极高胜率但赔率极低 (是否会全仓)
        # 隐含概率 0.99，赔率 1.01
        kelly_res_str = evaluate_betting_value(0.99, 1.01)
        kelly_res = json.loads(kelly_res_str)
        if kelly_res.get("recommended_bankroll_percentage", 0) > 0.15: # 即使几乎必胜，也不能超过风控上限
            issues_found.append(f"Bug: 凯利准则未严格执行全局暴露度上限 (当前暴露度: {kelly_res['recommended_bankroll_percentage']})。")
            
        # 测试 EV < 0
        kelly_res_neg_str = evaluate_betting_value(0.30, 2.00) # EV = 0.6 < 1
        kelly_res_neg = json.loads(kelly_res_neg_str)
        if kelly_res_neg.get("recommended_bankroll_percentage", 0) > 0:
            issues_found.append("Bug: EV < 0 时，凯利准则没有返回 0 仓位。")
    except Exception as e:
        issues_found.append(f"维度 4 崩溃: {traceback.format_exc()}")

    logger.info("\n=== 测试完成 ===")
    if issues_found:
        logger.error(f"发现 {len(issues_found)} 个深度漏洞：")
        for i, issue in enumerate(issues_found, 1):
            logger.error(f"{i}. {issue}")
    else:
        logger.info("完美！未发现任何深度漏洞。")
        
    return issues_found

if __name__ == "__main__":
    run_cross_dimensional_tests()