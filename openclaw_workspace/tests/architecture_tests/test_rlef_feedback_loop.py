import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import os
import asyncio
from dotenv import load_dotenv
from openclaw_workspace.tools.betting_ledger import BettingLedger
from openclaw_workspace.agents.auto_tuner_agent import AutoTunerAgent

async def test_rlef():
    load_dotenv()
    os.environ["AUTO_TUNER_USE_LLM"] = "true"
    
    # 1. Mock some DB records
    ledger = BettingLedger()
    
    # 模拟 ZSA 亏损 (因为门槛 -0.8 不够严格，被假新闻骗了)
    ledger.reset_economy("zsa_front_runner")
    res = ledger.execute_bet("zsa_front_runner", "M_001", "jingcai", "away_win", 2.0, 100.0)
    ledger.record_result(res["bet_id"], "LOSS", -100.0)
    res = ledger.execute_bet("zsa_front_runner", "M_002", "jingcai", "away_win", 2.0, 100.0)
    ledger.record_result(res["bet_id"], "LOSS", -100.0)
    
    # 模拟 Agentic OS 亏损
    ledger.reset_economy("agentic_os")
    res = ledger.execute_bet("agentic_os", "M_003", "jingcai", "home_win", 1.5, 100.0)
    ledger.record_result(res["bet_id"], "LOSS", -100.0)
    
    print("✅ 模拟真实环境账本数据注入完成...")
    
    # 2. 触发 RLEF
    tuner = AutoTunerAgent()
    print("🚀 触发 RLEF 环境反馈反思引擎...")
    result = await tuner.reflect_on_real_ledger()
    
    print("\n================ RLEF 结果 ================")
    print(f"状态: {result['status']}")
    print(f"反思: {result.get('reflection')}")
    print(f"新参数: {result.get('new_params', {}).get('zsa_thresholds')}")

if __name__ == "__main__":
    asyncio.run(test_rlef())