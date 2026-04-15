import asyncio
import logging
import time
import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.monte_carlo_simulator import TimeSliceMonteCarlo
from tools.settlement_engine import SettlementEngine
from agents.auto_tuner_agent import AutoTunerAgent
from core.event_bus import EventBus

logging.basicConfig(level=logging.ERROR, format='%(levelname)s - %(message)s')

async def run_deep_chaos_tests():
    print("\n" + "="*60)
    print("🌪️ CHAOS ENGINE V3: 全方位无死角深度破坏性测试 🌪️")
    print("="*60)

    # ---------------------------------------------------------
    # 维度 1: 数学引擎极限溢出 (The "Basketball Score" Attack)
    # ---------------------------------------------------------
    print("\n[维度 1: 数学引擎极限溢出 - 当足球踢出篮球比分]")
    simulator = TimeSliceMonteCarlo()
    try:
        # 传入极端的 xG (期望进球数)，例如两队实力极度悬殊或数据异常
        res = simulator.simulate_match(45.5, 0.1, simulations=1000)
        print(f"✅ 存活: Monte Carlo 成功处理极端 xG (45.5 vs 0.1).")
    except Exception as e:
        print(f"❌ 崩溃 (Monte Carlo): {e}")

    # ---------------------------------------------------------
    # 维度 2: 配置文件基因突变 (The "Amnesia" Attack)
    # ---------------------------------------------------------
    print("\n[维度 2: 配置文件损坏 - 基因库(JSON)被意外清空或写坏]")
    config_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'hyperparams.json')
    
    # 备份原配置
    with open(config_path, 'r') as f:
        backup = f.read()
        
    try:
        # 破坏配置文件
        with open(config_path, 'w') as f:
            f.write("{ invalid_json: 123, broken ")
            
        tuner = AutoTunerAgent()
        # 尝试让受损的 Agent 运行反思
        await tuner._reflect_and_evolve({"total_simulated": 1, "win_rate": 0, "roi": 0, "total_profit": 0, "details": []})
        print("✅ 存活: AutoTunerAgent 成功处理了损坏的 hyperparams.json.")
    except Exception as e:
        print(f"❌ 崩溃 (基因库损坏未隔离): {e}")
    finally:
        # 恢复配置
        with open(config_path, 'w') as f:
            f.write(backup)

    # ---------------------------------------------------------
    # 维度 3: 结算引擎的幽灵赛果 (The "Ghost Match" Attack)
    # ---------------------------------------------------------
    print("\n[维度 3: 结算引擎的幽灵赛果 - 遇到非标比分或大小写状态]")
    engine = SettlementEngine()
    try:
        # 测试 1: 退赛/弃权比分
        engine.determine_match_result(ft_score="W/O", status="FINISHED")
        print("✅ 存活: 成功处理 W/O 弃权比分.")
    except Exception as e:
        print(f"❌ 崩溃 (非标比分): {e}")
        
    try:
        # 测试 2: 状态大小写混合
        res = engine.determine_match_result(ft_score="", status="Cancelled")
        if res["status"] == "VOID":
            print("✅ 存活: 成功处理大小写混合的 Cancelled 状态.")
        else:
            print(f"❌ 逻辑错误: 未能正确 VOID 比赛.")
    except Exception as e:
        print(f"❌ 崩溃 (状态判断): {e}")

    # ---------------------------------------------------------
    # 维度 4: 异步总线的同步阻塞毒药 (The "Thread Blocker" Attack)
    # ---------------------------------------------------------
    print("\n[维度 4: 异步总线阻塞 - 当某个 Agent 发生了同步阻塞 (如 requests 库卡死)]")
    bus = EventBus()
    
    async def bad_sync_handler(data):
        # 模拟开发者错误地使用了同步的 time.sleep 而不是 asyncio.sleep
        # 或者使用了同步的 requests.get 卡死
        time.sleep(2)
        
    async def good_async_handler(data):
        await asyncio.sleep(0.1)
        
    def absolute_sync_handler(data):
        time.sleep(2)
        
    bus.subscribe("TEST_EVENT", absolute_sync_handler)
    bus.subscribe("TEST_EVENT", good_async_handler)
    
    start_time = time.time()
    await bus.publish("TEST_EVENT", {"data": "test"})
    # Event Bus should return immediately, not wait for the 2-second task
    elapsed = time.time() - start_time
    
    # Wait a bit to let the background tasks finish so we don't get "Task was destroyed but it is pending"
    await asyncio.sleep(2.5)
    
    if elapsed > 1.5:
        print(f"❌ 崩溃 (总线瘫痪): 一个糟糕的同步 Handler 阻塞了整个异步事件循环！耗时 {elapsed:.2f} 秒.")
    else:
        print(f"✅ 存活: 事件总线成功隔离了同步阻塞，耗时 {elapsed:.2f} 秒.")

if __name__ == "__main__":
    asyncio.run(run_deep_chaos_tests())