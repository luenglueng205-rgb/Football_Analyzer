import logging

logger = logging.getLogger(__name__)

class LiveMatchMonitor:
    """
    In-Play Hedging & Anomaly Monitor.
    Proactively calculates hedge EV and cash-out opportunities during live matches.
    """
    
    def __init__(self):
        self.active_bets = {}

    def register_live_bet(self, match_id: str, selection: str, stake: float, odds: float):
        """Register a bet to be monitored in-play."""
        self.active_bets[match_id] = {
            "selection": selection,
            "stake": stake,
            "odds": odds,
            "potential_return": stake * odds,
            "status": "active"
        }
        logger.info(f"Registered live bet {match_id} for hedging monitor. {selection} @ {odds} x {stake}")

    def evaluate_hedge_opportunity(self, match_id: str, current_score: str, live_odds_against: float, current_minute: int) -> dict:
        """
        Calculates if hedging the opposite outcome guarantees a profit.
        Formula: Hedge Stake = Target Profit / Live Odds Against
        """
        if match_id not in self.active_bets:
            return {"status": "unmonitored"}
            
        bet_info = self.active_bets[match_id]
        potential_return = bet_info["potential_return"]
        original_stake = bet_info["stake"]
        
        # Example: We bet Home Win.
        # "live_odds_against" represents the combined odds of (Draw OR Away Win)
        # We want to guarantee a profit P.
        # Hedge Stake * live_odds_against = potential_return
        
        required_hedge_stake = potential_return / live_odds_against
        total_investment = original_stake + required_hedge_stake
        
        guaranteed_profit = potential_return - total_investment
        roi = guaranteed_profit / total_investment if total_investment > 0 else 0
        
        # If ROI > 5% and we are past the 75th minute, strongly recommend hedging to secure profit
        action = "HEDGE_NOW" if roi > 0.05 and current_minute >= 75 else "HOLD"
        
        if action == "HEDGE_NOW":
            logger.warning(f"🚨 HEDGE ALERT: Match {match_id} - Score: {current_score} (Min {current_minute})")
            logger.warning(f"Original Stake: {original_stake}, Hedge Stake: {required_hedge_stake:.2f}")
            logger.warning(f"Guaranteed Profit: {guaranteed_profit:.2f} (ROI: {roi*100:.1f}%)")
            
        return {
            "match_id": match_id,
            "current_score": current_score,
            "minute": current_minute,
            "required_hedge_stake": round(required_hedge_stake, 2),
            "guaranteed_profit": round(guaranteed_profit, 2),
            "roi": round(roi, 3),
            "recommended_action": action
        }
