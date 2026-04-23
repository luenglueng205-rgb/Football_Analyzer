import json
import logging
from tools.betting_ledger import BettingLedger

logger = logging.getLogger(__name__)

def generate_simulated_ticket(match: str, play_type: str, selection: str, odds: float, stake: float, confidence: float, reasoning: str, lottery_type: str = "JINGCAI") -> str:
    """
    Generate a 500.com style simulated bet slip in Markdown format.
    Instead of physical printing, this returns a beautiful virtual ticket for the user.
    同时，它会在底层静默调用 BettingLedger，将这笔交易记录在案，作为 AI 赛后复盘和进化的痛觉基础。
    """
    expected_return = stake * odds
    
    # 【灵魂注入】强制账本入库 (Skin in the Game)
    ledger_msg = ""
    try:
        # 如果不是空仓(Skip)，则记入账本
        if "空仓" not in selection and "Skip" not in selection and stake > 0:
            ledger = BettingLedger()
            # 简单的将 match 拆分为 match_id (在真实系统中应传入准确的 id)
            match_id = match.replace(" ", "_") 
            res = ledger.execute_bet(match_id=match_id, lottery_type=lottery_type, selection=selection, odds=odds, stake=stake)
            if res.get("status") == "success":
                ledger_msg = f"\n*✅ 账本底层已同步扣除虚拟本金 ¥{stake:.2f}。当前凭证号: {res.get('ticket_code')}。赛后将触发自动复盘。*"
            else:
                ledger_msg = f"\n*⚠️ 账本记录失败: {res.get('message')}*"
    except Exception as e:
        logger.error(f"账本写入失败: {e}")
        ledger_msg = f"\n*⚠️ 账本写入异常: {e}*"

    markdown_ticket = f"""
### 🎟️ 500.com 模拟选号单 (Simulated Ticket)

| 赛事 (Match) | 玩法 (Market) | 选项 (Selection) | 赔率 (Odds) | 投入 (Stake) | 预计回报 (Return) |
|-------------|---------------|------------------|-------------|-------------|-------------------|
| **{match}** | `{play_type}` | **{selection}**  | {odds:.2f}  | ¥{stake:.2f} | **¥{expected_return:.2f}** |

- **🧠 AI 信心指数 (Confidence)**: {confidence * 100:.1f}%
- **💡 策略大脑洞察 (Strategist Reasoning)**: {reasoning}

*注：本单为 AI 原生模拟选号，非真实出票。*{ledger_msg}
"""
    return json.dumps({"simulated_ticket_markdown": markdown_ticket, "ledger_status": "executed" if ledger_msg and "✅" in ledger_msg else "skipped"}, ensure_ascii=False)
