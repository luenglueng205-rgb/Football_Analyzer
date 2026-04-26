import os
import sqlite3

from tools.betting_ledger import BettingLedger
from tools.clv_calculator import calculate_clv


def test_clv_calculation_and_backfill():
    db_path = "test_clv_ledger.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    ledger = BettingLedger(db_path=db_path)
    ledger.execute_bet("MCI_ARS", "jingcai", "主胜", 2.0, 100)
    ledger.record_closing_odds("MCI_ARS", 1.8)
    ledger.record_result("MCI_ARS", "LOSE", -100.0)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT odds, closing_odds, result, pnl FROM bets WHERE match_id='MCI_ARS' ORDER BY id DESC LIMIT 1")
    odds, closing_odds, result, pnl = c.fetchone()
    conn.close()

    assert odds == 2.0
    assert closing_odds == 1.8
    assert result == "LOSE"
    assert pnl == -100.0

    clv_res = calculate_clv(placed_odds=odds, closing_odds=closing_odds)
    assert clv_res["ok"] is True
    assert clv_res["data"]["clv"] < 0

    if os.path.exists(db_path):
        os.remove(db_path)


if __name__ == "__main__":
    test_clv_calculation_and_backfill()
    print("test_clv_calculation_and_backfill PASSED")

