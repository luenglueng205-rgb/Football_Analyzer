import itertools
from typing import List, Dict, Any

class ParlayFilterMatrix:
    def __init__(self):
        pass

    def calculate_parlay(self, matches: List[Dict[str, Any]], parlay_type: str, total_stake: float) -> Dict[str, Any]:
        """
        Calculate parlay combinations and returns.
        matches format: [{"match_id": "001", "selection": "主胜", "odds": 2.0}, ...]
        parlay_type: "2x1", "3x1", "3x4" (three 2x1s + one 3x1)
        """
        n_matches = len(matches)
        combinations = []
        
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

        max_return = sum(c["combined_odds"] * c["stake"] for c in combinations)
        
        return {
            "status": "success",
            "parlay_type": parlay_type,
            "total_cost": total_stake,
            "combinations": combinations,
            "max_potential_return": round(max_return, 2)
        }
