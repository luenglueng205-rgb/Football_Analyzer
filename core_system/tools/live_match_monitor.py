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

    def evaluate_complex_hedge(self, match_id: str, live_markets: dict, current_minute: int) -> dict:
        """
        支持多盘口的联合对冲计算器。计算如何分配本金买断剩余所有可能性以锁定利润。
        """
        if match_id not in self.active_bets:
            return {"hedge_recommended": False, "reason": "No active bet found"}
            
        bet = self.active_bets[match_id]
        potential_return = bet["stake"] * bet["odds"]
        
        # Calculate sum of inverse odds for all remaining live markets
        # IF sum(1/odds) < 1, an arbitrage (hedge) opportunity exists
        implied_prob_sum = sum(1.0 / odds for odds in live_markets.values())
        
        if implied_prob_sum == 0:
            return {"hedge_recommended": False, "reason": "No valid live markets provided"}
            
        # We need to guarantee a payout of `target_payout` regardless of outcome
        # For each market: hedge_stake * odds = target_payout
        # Total hedge investment = sum(target_payout / odds) = target_payout * implied_prob_sum
        # We want: potential_return - Total hedge investment > 0
        # Let's set target_payout = potential_return to perfectly flatten the risk
        
        total_hedge_investment = potential_return * implied_prob_sum
        
        if total_hedge_investment < potential_return - bet["stake"]:
            # Profitable hedge
            hedge_distribution = {
                market: round(potential_return / odds, 2)
                for market, odds in live_markets.items()
            }
            guaranteed_profit = potential_return - total_hedge_investment - bet["stake"]
            
            return {
                "hedge_recommended": True,
                "current_minute": current_minute,
                "total_hedge_cost": round(total_hedge_investment, 2),
                "guaranteed_net_profit": round(guaranteed_profit, 2),
                "hedge_distribution": hedge_distribution
            }
            
        return {
            "hedge_recommended": False,
            "reason": "Hedge cost too high, no guaranteed profit",
            "cost": round(total_hedge_investment, 2),
            "potential_return": potential_return
        }

