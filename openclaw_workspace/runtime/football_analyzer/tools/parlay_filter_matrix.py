import itertools
from typing import List, Dict, Any

class ParlayFilterMatrix:
    def __init__(self):
        pass

    def generate_parlays(self, candidates: List[Dict[str, Any]], parlay_type: str, stake: float = 100.0) -> List[Dict[str, Any]]:
        """
        Generate valid parlay combinations from a list of candidate legs, 
        filtering out invalid combinations (like same match mutex).
        Also applies max payout caps (e.g., 200,000 for 2-3 legs).
        """
        valid_parlays = []
        
        # Determine how many legs per combination based on parlay_type
        try:
            n_legs = int(parlay_type.split("x")[0])
        except (ValueError, IndexError):
            return []
            
        for comb in itertools.combinations(candidates, n_legs):
            match_ids = [leg.get("match_id") for leg in comb if leg.get("match_id")]
            
            # Same match mutex check
            if len(set(match_ids)) < len(match_ids):
                continue
                
            combined_odds = 1.0
            for leg in comb:
                combined_odds *= leg.get("odds", 1.0)
            
            theoretical_return = combined_odds * stake
            
            # Apply Max Payout Cap
            if n_legs <= 3:
                max_cap = 200000.0
            elif n_legs <= 5:
                max_cap = 500000.0
            else:
                max_cap = 1000000.0
                
            capped_return = min(theoretical_return, max_cap)
                
            valid_parlays.append({
                "type": parlay_type,
                "legs": list(comb),
                "combined_odds": round(combined_odds, 2),
                "stake": stake,
                "max_potential_return": round(capped_return, 2)
            })
                
        return valid_parlays

    def calculate_parlay(self, matches: List[Dict[str, Any]], parlay_type: str, total_stake: float) -> Dict[str, Any]:
        """
        Calculate parlay combinations and returns.
        matches format: [{"match_id": "001", "selection": "主胜", "odds": 2.0}, ...]
        parlay_type: "2x1", "3x1", "3x4" (three 2x1s + one 3x1)
        """
        n_matches = len(matches)
        combinations = []
        
        # Check for same match mutex (同场互斥) before proceeding
        match_ids = [m.get("match_id") for m in matches if m.get("match_id")]
        if len(set(match_ids)) < len(match_ids):
            return {
                "status": "error",
                "message": "Invalid combination: same match mutex violated (同场比赛不能串关)."
            }
        
        if parlay_type == "2x1" and n_matches == 2:
            comb = matches
            combined_odds = comb[0]["odds"] * comb[1]["odds"]
            combinations.append({
                "type": "2x1",
                "matches": [m["match_id"] for m in comb],
                "combined_odds": round(combined_odds, 2),
                "stake": total_stake
            })
            
        elif parlay_type == "3x4" and n_matches == 3:
            # Three 2x1s
            per_bet_stake = total_stake / 4.0
            for comb in itertools.combinations(matches, 2):
                combined_odds = comb[0]["odds"] * comb[1]["odds"]
                combinations.append({
                    "type": "2x1",
                    "matches": [m["match_id"] for m in comb],
                    "combined_odds": round(combined_odds, 2),
                    "stake": per_bet_stake
                })
            # One 3x1
            combined_odds = matches[0]["odds"] * matches[1]["odds"] * matches[2]["odds"]
            combinations.append({
                "type": "3x1",
                "matches": [m["match_id"] for m in matches],
                "combined_odds": round(combined_odds, 2),
                "stake": per_bet_stake
            })
        else:
            return {"status": "error", "message": f"Unsupported parlay type {parlay_type} for {n_matches} matches."}

        # Apply max payout cap per combination and calculate total
        total_max_return = 0.0
        is_capped_any = False
        for c in combinations:
            theoretical_return = c["combined_odds"] * c["stake"]
            try:
                n_legs = int(c["type"].split("x")[0])
            except (ValueError, IndexError):
                n_legs = len(c["matches"])
                
            if n_legs <= 3:
                max_cap = 200000.0
            elif n_legs <= 5:
                max_cap = 500000.0
            else:
                max_cap = 1000000.0
                
            capped_return = min(theoretical_return, max_cap)
            total_max_return += capped_return
            if theoretical_return > max_cap:
                is_capped_any = True
            
            c["max_potential_return"] = round(capped_return, 2)
            c["is_capped"] = theoretical_return > max_cap

        return {
            "status": "success",
            "parlay_type": parlay_type,
            "total_cost": total_stake,
            "combinations": combinations,
            "max_potential_return": round(total_max_return, 2),
            "is_capped": is_capped_any
        }
