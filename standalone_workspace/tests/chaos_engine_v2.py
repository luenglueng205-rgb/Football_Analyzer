import asyncio
import logging
import time
import math
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.parlay_rules_engine import ParlayRulesEngine
from tools.lottery_router import LotteryRouter
from core.event_bus import EventBus
from agents.router_agent import RouterAgent

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def run_chaos_tests():
    print("\n" + "="*50)
    print("🔥 CHAOS ENGINE V2: 业务极限与代码腐败深度破坏性测试 🔥")
    print("="*50)

    # ---------------------------------------------------------
    # 测试 1: 组合爆炸攻击 (DoS 漏洞测试)
    # ---------------------------------------------------------
    print("\n[测试 1: 组合爆炸攻击 - 传统足彩引擎能否扛住极端输入?]")
    engine = ParlayRulesEngine()
    try:
        start_time = time.time()
        # 尝试传入极大的复式选择，看是否会卡死 CPU
        # 比如任选九场，传入 14场比赛，每场选了 3个结果 (全包)
        # 理论注数 = C(14,9) * 3^9 = 2002 * 19683 = 39,405,366 注
        result = engine.calculate_chuantong_combinations([3]*14, "renjiu")
        elapsed = time.time() - start_time
        print(f"✅ 存活: 成功计算出 {result} 注, 耗时 {elapsed:.4f} 秒.")
        if result > 20000:
             print("⚠️ 业务警报: 注数达到千万级别，现实中打票需要 7800 万元本金，系统缺乏【最大注数/金额风控】拦截！")
    except Exception as e:
        print(f"❌ 崩溃: {e}")

    # ---------------------------------------------------------
    # 测试 2: 畸形赔率黑洞 (数学模型漏洞测试)
    # ---------------------------------------------------------
    print("\n[测试 2: 畸形赔率黑洞 - 物理路由器能否拦截非法数据格式?]")
    router = LotteryRouter()
    try:
        malformed_ticket = {
            "legs": [
                {"match_id": "M1", "play_type": "WDL", "odds": -1.5}, # 负数赔率
                {"match_id": "M2", "play_type": "WDL", "odds": 0},    # 零赔率
                {"match_id": "M3", "play_type": "WDL", "odds": float('inf')} # 无限大赔率
            ]
        }
        res = router.route_and_validate("JINGCAI", malformed_ticket)
        print("❌ 崩溃（静默失败）: 路由器居然放行了包含负数、零和无限大赔率的假票！")
        print(f"返回结果: {res}")
    except Exception as e:
        print(f"✅ 存活（成功拦截）: {e}")

    # ---------------------------------------------------------
    # 测试 3: 事件总线并发海啸 (内存与异步泄漏测试)
    # ---------------------------------------------------------
    print("\n[测试 3: 事件总线海啸 - 瞬间涌入 1000 场比赛是否会导致 OOM 或死锁?]")
    bus = EventBus()
    router_agent = RouterAgent()
    
    processed_count = 0
    async def fast_handler(event):
        nonlocal processed_count
        processed_count += 1
        # 模拟轻微阻塞
        await asyncio.sleep(0.001)
        
    bus.subscribe("MATCH_UPCOMING", fast_handler)
    
    start_time = time.time()
    # 模拟周末五大联赛同时开赛，瞬间推送 1000 条事件
    tasks = [bus.publish("MATCH_UPCOMING", {"id": i}) for i in range(1000)]
    await asyncio.gather(*tasks)
    elapsed = time.time() - start_time
    
    if processed_count == 1000:
        print(f"✅ 存活: 成功处理 {processed_count} 条并发事件，无死锁，耗时 {elapsed:.4f} 秒.")
    else:
        print(f"❌ 崩溃: 发生丢包，仅处理了 {processed_count}/1000 条事件.")

if __name__ == "__main__":
    asyncio.run(run_chaos_tests())
