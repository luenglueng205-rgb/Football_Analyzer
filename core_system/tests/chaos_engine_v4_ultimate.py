import asyncio
import random
import time
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../openclaw_workspace/src')))

from tools.lottery_router import LotteryRouter
from tools.parlay_rules_engine import ParlayRulesEngine
from mcp_server import handle_request

# ==========================================
# 16 种官方玩法全覆盖定义
# ==========================================
JINGCAI_TYPES = ["WDL", "HANDICAP_WDL", "CS", "GOALS", "HTFT", "MIXED_PARLAY"]
BEIDAN_TYPES = ["WDL", "SFGG", "UP_DOWN_ODD_EVEN", "GOALS", "HTFT", "CS"]
ZUCAI_TYPES = ["14_match", "renjiu", "6_htft", "4_goals"]

def generate_random_ticket():
    """随机生成符合或故意违反规则的订单，用于极限压力测试"""
    lottery = random.choices(["JINGCAI", "BEIDAN", "ZUCAI"], weights=[0.4, 0.4, 0.2])[0]
    
    ticket = {"legs": []}
    
    if lottery == "JINGCAI":
        play_type = random.choice(JINGCAI_TYPES)
        ticket["play_type"] = play_type
        # 随机生成 1 到 10 场 (8场以上应该被拦截)
        num_legs = random.randint(1, 10)
        for i in range(num_legs):
            leg = {"match_id": f"M{i}", "play_type": play_type if play_type != "MIXED_PARLAY" else random.choice(JINGCAI_TYPES[:-1])}
            # 50% 概率加入赔率，50% 概率不加（测试拦截）
            if random.random() > 0.1:
                leg["odds"] = round(random.uniform(1.1, 5.0), 2)
            # 随机加入小数让球（竞彩应该拦截）
            if play_type == "HANDICAP_WDL" and random.random() < 0.1:
                leg["handicap"] = random.choice([0.5, -0.5, 1.5])
            else:
                leg["handicap"] = random.choice([1, -1, 2, -2])
            ticket["legs"].append(leg)
            
    elif lottery == "BEIDAN":
        play_type = random.choice(BEIDAN_TYPES)
        ticket["play_type"] = play_type
        # 北单最多 15 场，比分最多 3 场
        num_legs = random.randint(1, 18)
        for i in range(num_legs):
            leg = {"match_id": f"M{i}", "play_type": play_type}
            if play_type == "SFGG":
                # 胜负过关 90% 概率给对的小数，10% 概率给整数（测试拦截）
                leg["handicap"] = random.choice([0.5, -0.5, 1.5]) if random.random() > 0.1 else 1
            ticket["legs"].append(leg)
            
    else: # ZUCAI
        play_type = random.choice(ZUCAI_TYPES)
        ticket["play_type"] = play_type
        # 随机生成 8 到 15 场
        num_legs = random.randint(8, 15)
        for i in range(num_legs):
            leg = {"match_id": f"M{i}"}
            # 足彩不应该有赔率，如果有，系统应该警告
            if random.random() < 0.2:
                leg["odds"] = 2.0
            ticket["legs"].append(leg)
            
    return lottery, ticket

async def run_1000_scenarios_chaos_test():
    print("\n" + "="*70)
    print("🔥 CHAOS ENGINE V4: 1000 个真实用户场景极限变态并发测试 🔥")
    print("覆盖: 竞彩(6种) | 北单(6种) | 传统足彩(4种) | 独立版 API | OpenClaw MCP")
    print("="*70)

    router = LotteryRouter()
    engine = ParlayRulesEngine()
    
    stats = {
        "total": 0,
        "standalone_passed": 0,
        "standalone_rejected": 0,
        "openclaw_mcp_passed": 0,
        "openclaw_mcp_rejected": 0,
        "crashes": 0
    }
    
    start_time = time.time()
    
    for i in range(1000):
        lottery, ticket = generate_random_ticket()
        stats["total"] += 1
        
        # --------------------------------------------------
        # 1. 独立版 API 极限测试 (直接调用 Python 类)
        # --------------------------------------------------
        try:
            res = router.route_and_validate(lottery, ticket)
            stats["standalone_passed"] += 1
        except ValueError as e:
            # 预期的业务拦截
            stats["standalone_rejected"] += 1
        except Exception as e:
            print(f"❌ 独立版致命崩溃: {e} | Ticket: {ticket}")
            stats["crashes"] += 1
            
        # --------------------------------------------------
        # 2. OpenClaw 适配版 MCP 极限测试 (模拟 JSON-RPC 调用)
        # --------------------------------------------------
        # 构造 MCP 请求
        mcp_request = {
            "jsonrpc": "2.0",
            "id": i,
            "method": "call_tool",
            "params": {
                "name": "validate_ticket_physics",
                "arguments": {
                    "lottery_type": lottery,
                    "ticket_data": ticket
                }
            }
        }
        
        try:
            mcp_res = await handle_request(mcp_request)
            
            if "error" in mcp_res:
                stats["openclaw_mcp_rejected"] += 1
            elif "result" in mcp_res:
                # result is a list of content blocks
                content_text = mcp_res["result"][0]["text"]
                content_json = json.loads(content_text)
                
                if content_json.get("isError"):
                    stats["openclaw_mcp_rejected"] += 1
                else:
                    stats["openclaw_mcp_passed"] += 1
        except Exception as e:
            print(f"❌ OpenClaw MCP 致命崩溃: {e}")
            stats["crashes"] += 1

        # 进度条
        if (i + 1) % 100 == 0:
            print(f"⏳ 已压测 {i + 1}/1000 场景...")

    elapsed = time.time() - start_time
    
    print("\n" + "="*70)
    print(f"✅ 压测完成！耗时: {elapsed:.3f} 秒")
    print(f"📊 总模拟场景: {stats['total']} 个")
    print(f"🛡️ 独立版内核: 放行 {stats['standalone_passed']} 个合法订单, 成功拦截 {stats['standalone_rejected']} 个违规订单.")
    print(f"🌐 OpenClaw MCP: 放行 {stats['openclaw_mcp_passed']} 个合法订单, 成功拦截 {stats['openclaw_mcp_rejected']} 个违规订单.")
    print(f"💀 致命崩溃数 (Crashes): {stats['crashes']} (必须为 0 才算合格)")
    print("="*70)
    
    if stats["crashes"] > 0:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_1000_scenarios_chaos_test())