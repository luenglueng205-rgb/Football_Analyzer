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
from tools.atomic_skills import evaluate_betting_value, calculate_poisson_probability
from tools.mxn_calculator import MxnCalculator
from auto_tuner import AutoTuningEvolutionEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_destructive_tests():
    issues_found = []
    
    logger.info("=== 开始针对 OpenClaw/WorkBuddy 实战场景的破坏性测试 ===")
    
    # --- 维度 1: 数据毒化与极端异常 (Data Poisoning & Extreme Anomalies) ---
    logger.info("\n[破坏测试 1]: 数据毒化与极端异常")
    try:
        # 1.1 赔率倒挂与超高赔率陷阱
        logger.info("测试 1.1: 赔率倒挂 (EV 极度虚高) 是否会击穿风控上限")
        # 模拟外部接口被黑，返回了一个胜率 90% 但赔率高达 100.0 的必赢假象
        kelly_res_str = evaluate_betting_value(0.90, 100.0)
        kelly_res = json.loads(kelly_res_str)
        
        # 即使 EV 极高，凯利准则的 fraction 也绝对不能超过我们在 SOP 中规定的安全红线 (如 10% 或 15%)
        # 目前底层逻辑是 max(0.0, min(kelly * 0.25, 0.1))，所以绝对不能 > 0.1
        if kelly_res.get("recommended_bankroll_percentage", 0) > 0.10:
            issues_found.append(f"Bug (致命): 赔率诱导陷阱击穿了仓位风控上限！当前建议仓位: {kelly_res['recommended_bankroll_percentage']}")
        else:
            logger.info(f"风控成功拦截: 面对 100倍 必赢赔率，系统强制锁定最高仓位为 {kelly_res['recommended_bankroll_percentage']}")

        # 1.2 负数 xG 注入 (模型崩溃测试)
        logger.info("测试 1.2: 负数预期进球 (xG) 注入泊松分布")
        poisson_res_str = calculate_poisson_probability(-1.5, 2.0)
        # 泊松分布不支持负数 mu，底层 scipy.stats 会抛出 ValueError，我们必须捕获它并返回友好的 JSON error
        poisson_res = json.loads(poisson_res_str)
        if "error" not in poisson_res:
            issues_found.append("Bug: 泊松计算器未能拦截负数 xG 输入，返回了非错误格式的响应。")
        else:
            logger.info("风控成功拦截: 成功捕获并格式化了负数 xG 的异常。")
            
    except Exception as e:
        issues_found.append(f"破坏测试 1 崩溃: {traceback.format_exc()}")

    # --- 维度 2: 工具调用与模式漂移 (Tool Calling & Schema Drift) ---
    logger.info("\n[破坏测试 2]: OpenClaw/WorkBuddy 工具调用环境模拟")
    try:
        # 2.1 模拟 WorkBuddy 传入了非预期的类型 (字符串替代浮点数)
        logger.info("测试 2.1: 类型漂移 (String instead of Float)")
        smt = SmartMoneyTracker()
        try:
            # 模拟 LLM 幻觉或平台解析错误，把赔率传成了字符串
            res = smt.track_odds_movement("test_match", {"home": "2.10", "draw": "3.40", "away": "3.50"}, {"home": "1.85", "draw": "3.60", "away": "4.20"})
            if "error" not in res and not res.get("market_movement"):
                 issues_found.append("Bug: 聪明资金监控器在处理字符串赔率时未抛出错误也未正确计算。")
        except TypeError:
            issues_found.append("Bug (兼容性): 聪明资金监控器遇到字符串类型的赔率直接触发 TypeError 崩溃，未做兼容转换。")

        # 2.2 模拟大模型参数缺失
        logger.info("测试 2.2: 缺少必填参数的容错")
        xg_adjuster = PlayerImpactAdjuster()
        # 模拟大模型忘了传 xa90 和 minutes_share
        missing = [{"name": "Player X", "xg90": 0.5}] 
        res = xg_adjuster.calculate_xg_adjustment(1.5, missing)
        # 系统应该能使用 get('xa90', 0.0) 安全回退
        if res["adjusted_xg"] != 1.0: # 1.5 - 0.5 = 1.0
            issues_found.append(f"Bug: 缺少部分球员参数时计算错误。预期 1.0，实际 {res['adjusted_xg']}")
            
    except Exception as e:
        issues_found.append(f"破坏测试 2 崩溃: {traceback.format_exc()}")

    # --- 维度 3: 级联故障与系统降级 (Cascading Failures) ---
    logger.info("\n[破坏测试 3]: 级联故障与极端环境")
    try:
        # 3.1 聪明资金计算器处理极端缺失赔率 (例如某博彩公司未开出平局赔率)
        logger.info("测试 3.1: 缺失部分结果的赔率矩阵")
        smt = SmartMoneyTracker()
        res = smt.track_odds_movement("test_match", {"home": 2.0, "away": 1.8}, {"home": 1.5, "away": 2.5})
        # 即使没有 draw，它也不应该崩溃，并且应该能正确计算两项的隐含概率
        if "error" in res:
             issues_found.append(f"Bug: 聪明资金监控器无法处理只有胜负（如网球/篮球，或北单胜负过关）的盘口: {res['error']}")
        else:
             logger.info("兼容性验证: 成功处理了没有平局的残缺赔率矩阵。")

    except Exception as e:
        issues_found.append(f"破坏测试 3 崩溃: {traceback.format_exc()}")

    logger.info("\n=== 破坏性测试完成 ===")
    if issues_found:
        logger.error(f"🚨 发现 {len(issues_found)} 个深度漏洞：")
        for i, issue in enumerate(issues_found, 1):
            logger.error(f"{i}. {issue}")
    else:
        logger.info("✅ 完美！系统在所有破坏性测试下均坚如磐石，未发现任何崩溃或风控漏洞。")
        
    return issues_found

if __name__ == "__main__":
    run_destructive_tests()