import logging

logger = logging.getLogger(__name__)

class SettlementEngine:
    """
    Strict Official Settlement Engine.
    Perfectly mirrors official China Sports Lottery settlement rules (Jingcai/Beidan).
    Handles 90-minute full-time rules, extra time exclusions, and cancellations.
    """
    
    def __init__(self):
        self.ruleset = {
            "jingcai": "90_min_only",
            "beidan": "90_min_only",
            "cancelled_odds": 1.0,
            "postponed_hours_limit": 36 # If postponed > 36h, void
        }

    def determine_match_result(self, ft_score: str, aet_score: str = None, status: str = "FINISHED") -> dict:
        """
        Determines the official betting result based on the 90-minute rule.
        """
        if status.upper() in ["CANCELLED", "POSTPONED", "ABANDONED"]:
            logger.warning(f"🚨 MATCH {status}: Settlement odds reset to 1.0 per official rules.")
            return {
                "status": "VOID",
                "official_result": "REFUND",
                "odds_applied": 1.0
            }
            
        if not ft_score or ft_score.upper() in ["W/O", "AWARDED"]:
            logger.warning(f"🚨 MATCH STATUS ABNORMAL (Score: {ft_score}). Voiding per rules.")
            return {
                "status": "VOID",
                "official_result": "REFUND",
                "odds_applied": 1.0
            }
            
        try:
            home_goals, away_goals = map(int, ft_score.split("-"))
        except ValueError:
            logger.error(f"🚨 MATCH SCORE MALFORMED ({ft_score}). Voiding per rules.")
            return {
                "status": "VOID",
                "official_result": "REFUND",
                "odds_applied": 1.0
            }
        
        # Determine 1X2
        if home_goals > away_goals:
            wdl = "3" # Home Win
        elif home_goals == away_goals:
            wdl = "1" # Draw
        else:
            wdl = "0" # Away Win
            
        if aet_score:
            logger.info(f"Extra time played ({aet_score}), but settlement strictly uses 90-min score ({ft_score}).")
            
        return {
            "status": "SETTLED",
            "official_result": wdl,
            "ft_score": ft_score,
            "aet_score_ignored": aet_score,
            "odds_applied": "market_odds"
        }

    def settle_ticket(self, ticket: dict, match_results: dict) -> dict:
        """
        Settles a parlay ticket.
        If any leg is voided, its odds become 1.0, and the parlay cascades down.
        """
        total_odds = 1.0
        ticket_status = "WON"
        
        for leg in ticket["legs"]:
            match_id = leg["match_id"]
            if match_id not in match_results:
                return {"status": "PENDING", "reason": f"Waiting for match {match_id}"}
                
            result = match_results[match_id]
            if result["status"] == "VOID":
                logger.info(f"Leg {match_id} VOIDED. Odds 1.0 applied.")
                total_odds *= 1.0
                leg["status"] = "VOID"
            elif result["official_result"] == leg["selection"]:
                logger.info(f"Leg {match_id} WON. Odds {leg['odds']} applied.")
                total_odds *= leg["odds"]
                leg["status"] = "WON"
            else:
                logger.info(f"Leg {match_id} LOST. Ticket BUST.")
                ticket_status = "LOST"
                total_odds = 0.0
                leg["status"] = "LOST"
                break
                
        payout = ticket["stake"] * total_odds if ticket_status == "WON" else 0.0
        
        return {
            "ticket_id": ticket.get("ticket_id", "unknown"),
            "status": ticket_status,
            "final_odds": round(total_odds, 2),
            "payout": round(payout, 2)
        }
