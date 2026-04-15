import os
import sqlite3
from tools.betting_ledger import BettingLedger

def test_kpi_ledger():
    db_path = "test_kpi_ledger.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    ledger = BettingLedger(db_path=db_path)
    ledger.execute_bet("MCI_ARS", "jingcai", "主胜", 2.0, 100)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("PRAGMA table_info(bets)")
    columns = [col[1] for col in c.fetchall()]
    
    assert "closing_odds" in columns
    assert "result" in columns
    assert "pnl" in columns
    
    c.execute("SELECT match_id, odds, stake, closing_odds FROM bets WHERE match_id='MCI_ARS'")
    row = c.fetchone()
    assert row[0] == "MCI_ARS"
    assert row[1] == 2.0
    assert row[2] == 100.0
    assert row[3] is None
    
    conn.close()
    if os.path.exists(db_path):
        os.remove(db_path)
        
    print("test_kpi_ledger PASSED")

if __name__ == "__main__":
    test_kpi_ledger()