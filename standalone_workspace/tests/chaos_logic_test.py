import asyncio
import random
import time
import sys
from typing import List, Dict

# Mock the tools temporarily to force chaos conditions if needed,
# but for logic testing, we want to run the real agents with problematic inputs.

from agents.syndicate_os import SyndicateOS

class ChaosLogicTester:
    def __init__(self):
        self.os = SyndicateOS()
        
    async def run_test_suite(self):
        print("\n" + "="*60)
        print("🔥 [CHAOS TEST] 内部逻辑破坏性压力测试启动 🔥")
        print("="*60)
        
        tests = [
            self.test_case_1_gibberish_teams,
            self.test_case_2_extremely_long_context,
            self.test_case_3_conflicting_quant_reports,
        ]
        
        for i, test in enumerate(tests, 1):
            print(f"\n[{i}/{len(tests)}] 正在执行: {test.__name__}")
            try:
                start_time = time.time()
                # 设定严格超时，防止 Agent 死循环
                await asyncio.wait_for(test(), timeout=120.0)
                elapsed = time.time() - start_time
                print(f"✅ {test.__name__} 通过 (耗时: {elapsed:.2f}s)")
            except asyncio.TimeoutError:
                print(f"❌ {test.__name__} 失败: Agent 陷入死循环或执行超时 (>120s)")
            except Exception as e:
                print(f"❌ {test.__name__} 失败: 抛出异常 {type(e).__name__}: {e}")

    async def test_case_1_gibberish_teams(self):
        """测试 1：输入完全不存在的、甚至带有乱码和注入攻击的球队名称。
        目的：测试系统是否会因为找不到数据而崩溃，或者被 Prompt 注入。"""
        home = "火星流浪者队_DROP_TABLE_matches;--"
        away = "X AE A-12 FC ⚽️⚽️⚽️"
        
        print(f"  -> 输入: {home} vs {away}")
        res = await self.os.process_match(home, away, "竞彩足球")
        
        # 验证法官是否能够正确识别出这是无效比赛并 Skip
        decision = res.get("final_decision", "").lower()
        if "skip" not in decision and "放弃" not in decision:
            print("  ⚠️ 警告: 法官没有放弃这场荒谬的比赛！输出内容:", decision[:100])
        else:
            print("  -> 法官成功识别异常并放弃下注。")

    async def test_case_2_extremely_long_context(self):
        """测试 2：超长下注描述和极端彩种。
        目的：测试 LLM 的 Token 截断机制和指令遵循能力。"""
        home = "拜仁慕尼黑"
        away = "巴塞罗那"
        lottery_desc = "这是一个极度复杂的彩种：" + "胜平负"*500 # 模拟超长输入
        
        print("  -> 输入超长彩种描述...")
        res = await self.os.process_match(home, away, lottery_desc)
        if not res.get("final_decision"):
            raise ValueError("最终裁决为空")
        print("  -> 系统成功处理超长输入，未崩溃。")

    async def test_case_3_conflicting_quant_reports(self):
        """测试 3：强制让三大宽客陷入极度分歧（通过 Prompt 注入或者模拟）。
        这里我们直接走真实流程，看面对豪门对决时，三方的分歧是否会导致法官逻辑错乱。"""
        home = "皇家马德里"
        away = "曼彻斯特城"
        
        print(f"  -> 输入豪门对决: {home} vs {away}，观察多空博弈是否会导致法官宕机...")
        res = await self.os.process_match(home, away, "竞彩单关")
        
        debates = res.get("debates", {})
        if not debates.get("fundamentalist") or not debates.get("contrarian"):
            raise ValueError("部分宽客未按时提交报告")
            
        decision = res.get("final_decision", "")
        if len(decision) < 50:
            raise ValueError("法官的裁决过于简短，疑似幻觉或输出截断")
        print("  -> 三方宽客成功提交报告，法官裁决完成。")

if __name__ == "__main__":
    tester = ChaosLogicTester()
    asyncio.run(tester.run_test_suite())
