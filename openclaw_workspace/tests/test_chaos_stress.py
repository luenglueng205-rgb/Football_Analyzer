import asyncio
import time
import random
import sys
import os
import contextlib
import io

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from agents.ai_native_core import AINativeCoreAgent

# ==========================================
# 混沌工程 (Chaos Engineering) & 压力测试注入
# ==========================================

# 保存原始方法
original_execute = AINativeCoreAgent._execute_tool
original_process = AINativeCoreAgent.process

async def chaos_execute_tool(self, function_name, arguments):
    """模拟 MCP 工具调用时的各种极端网络与数据异常"""
    chaos_dice = random.random()
    if chaos_dice < 0.05:
        # 5% 概率：API 彻底超时 (Timeout)
        await asyncio.sleep(0.5)
        raise TimeoutError(f"Chaos: {function_name} API Timeout")
    elif chaos_dice < 0.10:
        # 5% 概率：返回极其残缺的脏数据 (Dirty Data)
        return {"error": "HTTP 502 Bad Gateway", "data": None}
    elif chaos_dice < 0.20:
        # 10% 概率：网络高延迟 (High Latency)
        await asyncio.sleep(1.5)
        
    return await original_execute(self, function_name, arguments)

async def chaos_process(self, state):
    """模拟大模型主脑层面的崩溃"""
    chaos_dice = random.random()
    if chaos_dice < 0.02:
        # 2% 概率：大模型上下文溢出或内存泄漏 (OOM/Context Overflow)
        raise MemoryError("Chaos: LLM Context Window Overflow")
        
    return await original_process(self, state)

# 注入混沌变异
AINativeCoreAgent._execute_tool = chaos_execute_tool
AINativeCoreAgent.process = chaos_process

async def run_stress_test(concurrency=50):
    print(f"\n🚀 [Chaos & Stress Test] 正在启动深度破坏性压力测试...")
    print(f"⚡️ 并发量: {concurrency} 个 AI 智能体同时分析不同的比赛")
    print(f"🌪  破坏性注入: 开启 (模拟 5% API超时, 5% 脏数据, 10% 高延迟, 2% 内存溢出)")
    
    agent = AINativeCoreAgent()
    
    async def task(i):
        state = {
            "current_match": {"league": "英超", "home_team": f"主队_{i}", "away_team": f"客队_{i}"},
            "params": {"lottery_type": "beijing"}
        }
        try:
            start = time.time()
            # 屏蔽内部打印，防止控制台刷屏爆炸
            with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                res = await agent.process(state)
            cost = time.time() - start
            return {"status": "success", "cost": cost, "id": i}
        except MemoryError as me:
            return {"status": "error", "error": f"MemoryError: {me}", "id": i}
        except Exception as e:
            return {"status": "error", "error": f"Exception: {e}", "id": i}

    start_time = time.time()
    
    # 核心并发执行
    results = await asyncio.gather(*(task(i) for i in range(concurrency)))
    
    total_time = time.time() - start_time
    
    success = sum(1 for r in results if r["status"] == "success")
    errors = sum(1 for r in results if r["status"] == "error")
    
    error_types = {}
    for r in results:
        if r["status"] == "error":
            e_type = r["error"].split(":")[0]
            error_types[e_type] = error_types.get(e_type, 0) + 1

    print("\n" + "="*60)
    print("📊 [Test Report] 2026 AI-Native 破坏性压力测试报告")
    print("="*60)
    print(f"总并发任务数 : {concurrency} 场比赛同时分析")
    print(f"总执行耗时   : {total_time:.2f} 秒")
    print(f"系统吞吐量   : {concurrency/total_time:.2f} 任务/秒 (TPS)")
    print("-" * 60)
    print(f"✅ 成功容灾数 : {success} (系统成功降级或拦截异常，未崩溃)")
    print(f"❌ 致命崩溃数 : {errors} (被混沌工程彻底击穿)")
    
    if errors > 0:
        print("\n⚠️ 崩溃原因分布:")
        for k, v in error_types.items():
            print(f"  - {k}: {v} 次")
            
    print("="*60)
    
    if errors == 0:
        print("🏆 结论: 系统具备极高的容错性与并发能力，准许上生产环境！")
    elif errors < concurrency * 0.05:
        print("🟡 结论: 系统基本稳定，极少数极端变异导致崩溃，可带伤上线。")
    else:
        print("❌ 结论: 系统架构存在脆弱点，未能扛住破坏性测试，需回炉重造！")

if __name__ == "__main__":
    # 强制忽略 OpenAI Pydantic 警告
    import warnings
    warnings.filterwarnings("ignore")
    asyncio.run(run_stress_test(100)) # 暴力拉到 100 并发
