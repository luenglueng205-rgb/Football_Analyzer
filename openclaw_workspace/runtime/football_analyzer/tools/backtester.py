import json
import sqlite3
from typing import Dict, Any

class SnapshotBacktester:
    """
    P3 回测验证引擎：读取本地的 SnapshotStore 快照进行回测验证。
    """
    def __init__(self, db_path: str = "data/snapshots.db"):
        self.db_path = db_path

    def get_all_matches(self):
        """获取所有已保存过快照的比赛列表"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT DISTINCT match_id, home_team, away_team FROM matches")
        rows = c.fetchall()
        conn.close()
        
        matches = []
        for r in rows:
            matches.append({
                "match_id": r[0],
                "home_team": r[1],
                "away_team": r[2]
            })
        return matches

    def run_backtest(self, match_id: str, ai_decision: str, actual_result: str) -> Dict[str, Any]:
        """
        执行单场比赛的回测
        """
        # 1. 验证 AI 的投资决策是否正确
        if ai_decision.lower() == 'skip':
            return {"match_id": match_id, "pnl": 0.0, "status": "skipped", "message": "AI 主动放弃（风控成功）"}
            
        is_win = (ai_decision.lower() == actual_result.lower())
        # 假设单注 100 元，基准赔率 2.0
        if is_win:
            return {"match_id": match_id, "pnl": 100.0, "status": "win", "message": "✅ 投注成功，精准命中"}
        else:
            return {"match_id": match_id, "pnl": -100.0, "status": "lose", "message": "❌ 投注失败，模型误判"}

if __name__ == "__main__":
    bt = SnapshotBacktester()
    matches = bt.get_all_matches()
    print("==================================================")
    print("📊 [P3 回测验证引擎] Snapshot Backtester 启动")
    print("==================================================")
    print(f"找到 {len(matches)} 场可用于回测的历史比赛快照。")
    for m in matches:
        print(f" - {m['home_team']} vs {m['away_team']} (ID: {m['match_id']})")
        
    print("\n[测试] 假设 AI 选择了 'skip'...")
    res = bt.run_backtest(matches[0]['match_id'] if matches else "test", "skip", "home")
    print(f"回测结果: {res}")
