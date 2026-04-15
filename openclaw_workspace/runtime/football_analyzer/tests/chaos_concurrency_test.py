import asyncio
from agents.syndicate_os import SyndicateOS

async def run_single(match_id, home, away):
    os_system = SyndicateOS()
    print(f"[{match_id}] 开始分析: {home} vs {away}")
    try:
        # 为了不消耗太多真实 Token，我们这里只是看 DB 是否因为并发锁死
        res = await os_system.process_match(home, away, "单关")
        decision = res.get("final_decision", "")
        print(f"[{match_id}] 结束分析. 裁决: {decision[:20]}...")
        return res
    except Exception as e:
        print(f"[{match_id}] 抛出异常: {e}")
        return e

async def run_concurrency_chaos():
    print("\n" + "="*60)
    print("🔥 [CHAOS TEST 2] 高并发锁竞争测试启动 🔥")
    print("="*60)
    
    matches = [
        ("M1", "巴塞罗那", "皇家马德里"),
        ("M2", "拜仁慕尼黑", "多特蒙德"),
        ("M3", "阿森纳", "切尔西"),
        ("M4", "曼联", "利物浦"),
        ("M5", "尤文图斯", "马德里竞技"),
    ]
    
    # 并发启动 5 场比赛的分析，这会让它们同时去读写 ChromaDB 和 SQLite
    results = await asyncio.gather(*(run_single(*m) for m in matches), return_exceptions=True)
    
    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        print(f"\n❌ 并发测试失败：发现 {len(errors)} 个致命并发错误 (如 Database is locked)")
        for e in errors:
            print(f"  -> {e}")
    else:
        print("\n✅ 系统在 5 并发压力下存活，未发生 SQLite / ChromaDB 数据库死锁！")

if __name__ == "__main__":
    asyncio.run(run_concurrency_chaos())
