import os
import sqlite3
from tools.betting_ledger import BettingLedger

def test_ledger_initialization_and_bet():
    db_path = "test_ledger.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    ledger = BettingLedger(db_path=db_path)
    
    # Check initial bankroll
    status = ledger.check_bankroll()
    assert status["current_bankroll"] == 10000.0
    
    # Execute a bet
    result = ledger.execute_bet(
        match_id="20260414_RM_MCI",
        lottery_type="jingcai",
        selection="主胜",
        odds=2.80,
        stake=1000.0
    )
    
    assert result["status"] == "success"
    assert "jingcai|20260414_RM_MCI|主胜@2.8" in result["ticket_code"]
    
    # Check updated bankroll
    status = ledger.check_bankroll()
    assert status["current_bankroll"] == 9000.0
    assert status["total_bets"] == 1
    
    if os.path.exists(db_path):
        os.remove(db_path)
        
    print("test_ledger_initialization_and_bet PASSED")

if __name__ == "__main__":
    test_ledger_initialization_and_bet()
