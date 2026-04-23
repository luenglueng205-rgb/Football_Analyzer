import logging

logger = logging.getLogger(__name__)

class PreMatchSentinel:
    """
    T-30 Lineup & Pre-Match Monitor.
    Proactively checks for missing key players or sudden market shifts 30 minutes before kick-off.
    """
    
    def __init__(self):
        self.monitored_matches = {}

    def register_match(self, match_id: str, key_players: list, original_ev: float):
        """Register a match to be monitored before kick-off."""
        self.monitored_matches[match_id] = {
            "key_players": key_players,
            "original_ev": original_ev,
            "status": "monitored"
        }
        logger.info(f"Registered match {match_id} for T-30 lineup monitoring. Key players: {key_players}")

    def check_lineups_t30(self, match_id: str, actual_starting_xi: list) -> dict:
        """
        Check if the key players are actually starting.
        If a key player is missing, the EV drops significantly.
        """
        if match_id not in self.monitored_matches:
            return {"status": "unmonitored"}
            
        match_info = self.monitored_matches[match_id]
        key_players = match_info["key_players"]
        
        missing_players = [p for p in key_players if p not in actual_starting_xi]
        
        if missing_players:
            logger.warning(f"🚨 ALERT: Match {match_id} - Key players missing from starting XI: {missing_players}")
            # Simulate a 15% drop in EV per missing key player
            new_ev = match_info["original_ev"] * (1 - (0.15 * len(missing_players)))
            
            action = "CANCEL_BET" if new_ev < 1.05 else "PROCEED_WITH_CAUTION"
            
            return {
                "match_id": match_id,
                "status": "anomaly_detected",
                "missing_players": missing_players,
                "original_ev": match_info["original_ev"],
                "adjusted_ev": round(new_ev, 3),
                "recommended_action": action
            }
            
        return {
            "match_id": match_id,
            "status": "lineups_confirmed",
            "recommended_action": "PROCEED"
        }
