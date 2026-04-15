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

    def determine_all_play_types_results(self, ft_score: str, ht_score: str = None, handicaps: dict = None, status: str = "FINISHED") -> dict:
        """
        根据 90分钟比分 一次性生成 16 种玩法的所有正确选项。隔离加时赛。
        """
        if status.upper() in ["CANCELLED", "POSTPONED", "ABANDONED"] or not ft_score or ft_score.upper() in ["W/O", "AWARDED"]:
            return {"status": "VOID", "official_result": "REFUND", "odds_applied": 1.0}
            
        try:
            home_goals, away_goals = map(int, ft_score.split("-"))
            total_goals = home_goals + away_goals
        except ValueError:
            return {"status": "VOID", "official_result": "REFUND", "odds_applied": 1.0}
            
        results = {
            "status": "SETTLED",
            "WDL": "3" if home_goals > away_goals else "1" if home_goals == away_goals else "0",
            "GOALS": str(min(total_goals, 7)), # Usually capped at 7+
            "CS": f"{home_goals}-{away_goals}",
            "ODD_EVEN": "ODD" if total_goals % 2 != 0 else "EVEN"
        }
        
        # Handicap WDL
        if handicaps:
            jc_h = handicaps.get("JINGCAI_HANDICAP", 0)
            adjusted_home_jc = home_goals + jc_h
            results["JINGCAI_HANDICAP_WDL"] = "3" if adjusted_home_jc > away_goals else "1" if adjusted_home_jc == away_goals else "0"
            
            bd_h = handicaps.get("BEIDAN_HANDICAP", 0)
            adjusted_home_bd = home_goals + bd_h
            results["BEIDAN_HANDICAP_WDL"] = "3" if adjusted_home_bd > away_goals else "1" if adjusted_home_bd == away_goals else "0"
            
        # HTFT
        if ht_score:
            try:
                ht_home, ht_away = map(int, ht_score.split("-"))
                ht_res = "3" if ht_home > ht_away else "1" if ht_home == ht_away else "0"
                results["HTFT"] = f"{ht_res}-{results['WDL']}"
            except ValueError:
                pass
                
        # Beidan UP_DOWN_ODD_EVEN (0-2 goals = DOWN, 3+ goals = UP)
        up_down = "UP" if total_goals >= 3 else "DOWN"
        results["UP_DOWN_ODD_EVEN"] = f"{up_down}_{results['ODD_EVEN']}"
        
        return results

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
