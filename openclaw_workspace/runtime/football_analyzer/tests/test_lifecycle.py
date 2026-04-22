import sys
import os
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.pre_match_sentinel import PreMatchSentinel
from tools.live_match_monitor import LiveMatchMonitor
from tools.settlement_engine import SettlementEngine

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_complex_live_hedging():
    monitor = LiveMatchMonitor()
    
    # 初盘买了比分 1-0
    monitor.register_live_bet("M1", "CS_1-0", 100, 7.0)
    
    # 走地80分钟，比分已经是 1-0，需要对冲剩下的所有可能（其他比分）
    live_markets = {
        "CS_1-1": 15.0,
        "CS_2-0": 12.0,
        "CS_OTHER": 20.0
    }
    
    result = monitor.evaluate_complex_hedge("M1", live_markets, 80)
    
    assert result["hedge_recommended"] is True
    assert "hedge_distribution" in result

def run_tests():
    print("\n--- Testing Pre-Match Sentinel (T-30 Lineups) ---")
    sentinel = PreMatchSentinel()
    sentinel.register_match("ARS_vs_MUN", ["Saka", "Odegaard", "Saliba"], 1.15)
    
    # Simulate Saka missing
    actual_xi = ["Odegaard", "Saliba"]
    res = sentinel.check_lineups_t30("ARS_vs_MUN", actual_xi)
    print(f"Action taken: {res['recommended_action']} | Adjusted EV: {res.get('adjusted_ev')}")
    
    print("\n--- Testing Live Match Monitor (Hedging) ---")
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("RMA_vs_LIV", "Home Win", 100.0, 2.5)
    
    # 76th min, 1-0 up, live odds for Draw/Away are 4.5
    res = monitor.evaluate_hedge_opportunity("RMA_vs_LIV", "1-0", 4.5, 76)
    print(f"Action taken: {res['recommended_action']} | Required Hedge Stake: {res.get('required_hedge_stake')}")
    print(f"Guaranteed Profit: {res.get('guaranteed_profit')} | ROI: {res.get('roi')}")
    
    print("\n--- Testing Settlement Engine (Official Rules) ---")
    engine = SettlementEngine()
    
    # Normal win
    res = engine.determine_match_result("2-1")
    print(f"FT Score 2-1 -> Official Result: {res['official_result']}")
    
    # Extra time scenario (1-1 at 90m, 2-1 AET)
    res = engine.determine_match_result("1-1", "2-1")
    print(f"FT 1-1, AET 2-1 -> Official Result: {res['official_result']} (Strictly uses 90-min score)")
    
    # Cancelled match
    res = engine.determine_match_result("", status="CANCELLED")
    print(f"Status CANCELLED -> Applied Odds: {res['odds_applied']}")
    
    # Settle ticket
    ticket = {
        "ticket_id": "TICKET_001",
        "stake": 100.0,
        "legs": [
            {"match_id": "M1", "selection": "3", "odds": 2.0},
            {"match_id": "M2", "selection": "1", "odds": 3.0} # This will be cancelled
        ]
    }
    match_results = {
        "M1": {"status": "SETTLED", "official_result": "3", "odds_applied": 2.0},
        "M2": {"status": "VOID", "official_result": "REFUND", "odds_applied": 1.0}
    }
    res = engine.settle_ticket(ticket, match_results)
    print(f"Ticket Settlement -> Status: {res['status']} | Final Odds: {res['final_odds']} | Payout: {res['payout']}")

if __name__ == "__main__":
    run_tests()
