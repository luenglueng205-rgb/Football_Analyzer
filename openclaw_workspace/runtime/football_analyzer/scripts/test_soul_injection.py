import asyncio
import os
import sys

# Add standalone_workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.memory_manager import MemoryManager
from agents.ai_native_core import AINativeCoreAgent

async def run_soul_injection_test():
    print("\n" + "="*50)
    print("🧠 启动数字生命“灵魂注入”测试 (Memory Recall & Skin in the Game)")
    print("="*50)
    
    # 1. 预先向 ChromaDB 注入一段“历史教训”
    print("\n[系统动作] 正在向 ChromaDB 注入“皇家马德里”的历史惨痛教训...")
    mm = MemoryManager()
    mm.save_insight(
        team_name="皇家马德里", 
        insight_text="【历史血泪教训】2025年发现：皇马在客场面对摆大巴的弱队时，由于缺少强力破局点，极易陷入 0:0 或 1:1 闷平。切勿在客场盲目重注皇马让球！",
        match_id="historical_mock_001"
    )
    print("[系统动作] 记忆注入完成。")
    
    # 2. 启动 AI 分析
    agent = AINativeCoreAgent()
    
    # 我们故意设置一场皇马客场的比赛，看看 AI 能不能想起来，并作出防守性决策，最后看它有没有记账
    case = {
        "lottery": "JINGCAI",
        "match": "马洛卡 vs 皇家马德里",
        "league": "西甲",
        "odds": "8.50 / 4.80 / 1.35",
        "desc": "测试灵魂闭环：AI 是否能召回刚注入的记忆，修改决策，并最终将决策写入 BettingLedger？"
    }
    
    print(f"\n[测试开始] {case['desc']}")
    print(f"比赛: {case['match']} ({case['league']}) - 赔率: {case['odds']}")
    print("-" * 30)
    
    try:
        state = {
            "current_match": {"home_team": case["match"].split(" vs ")[0], "away_team": case["match"].split(" vs ")[1]},
            "params": {"lottery_type": case["lottery"].lower(), "lottery_desc": case["lottery"]}
        }
        result = await agent.process(state)
        print("\n【AI 分析与出票结果】:\n")
        print(result.get("ai_native_report", result))
    except Exception as e:
        print(f"执行失败: {e}")
        
    print("\n[系统动作] 正在检查 SQLite 账本，验证决策是否成功入库...")
    from tools.betting_ledger import BettingLedger
    ledger = BettingLedger()
    
    # Fetch the latest bet
    import sqlite3
    conn = sqlite3.connect(ledger.db_path)
    c = conn.cursor()
    c.execute("SELECT match_id, lottery_type, selection, odds, stake, ticket_code FROM bets ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    
    if row:
        print(f"✅ 账本核对成功！AI 刚刚下注了: 比赛={row[0]}, 玩法={row[1]}, 选项={row[2]}, 金额={row[4]}, 凭证号={row[5]}")
    else:
        print("❌ 账本为空，灵魂注入失败！")
    
    print("="*50)

if __name__ == "__main__":
    asyncio.run(run_soul_injection_test())
