import os
import requests
from typing import Dict, Any, List

class ForeignAPIClient:
    """
    P4 阶段：国外付费 API 客户端 (The Odds API, API-Football 等)
    作为高质量结构化数据的第一选择，失败后降级到 AgentBrowser。
    """
    def __init__(self):
        self.odds_api_key = os.getenv("ODDS_API_KEY", "fb47ab523dd9db967003590d76ec9074")
        self.api_football_key = os.getenv("API_FOOTBALL_KEY", "ac143a21c2fa6ffdfe8716b7424fc4f8")
        
        # Mapping English to Chinese is hard without a DB, but we do our best 
        # or rely on the AI to understand the English names.
    
    def get_odds(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """
        Fetch from The Odds API.
        Note: The Odds API uses English team names, so we just fetch all soccer odds and try to find a match,
        or return the top matches for the AI to analyze.
        """
        try:
            url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={self.odds_api_key}&regions=eu,uk&markets=h2h"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # For simplicity, if we have data, we return the first few matches
            # The AI can use this structured data to calculate EV.
            if isinstance(data, list) and len(data) > 0:
                # Format it nicely
                matches = []
                for m in data[:5]:
                    bookmakers = m.get("bookmakers", [])
                    if not bookmakers: continue
                    best_odds = bookmakers[0].get("markets", [])[0].get("outcomes", [])
                    matches.append({
                        "home_team_en": m["home_team"],
                        "away_team_en": m["away_team"],
                        "commence_time": m["commence_time"],
                        "odds": best_odds
                    })
                return {
                    "ok": True,
                    "data": {"foreign_api_odds": matches},
                    "error": None,
                    "meta": {"source": "the_odds_api", "confidence": 0.95, "mock": False, "stale": False}
                }
        except Exception as e:
            print(f"[ForeignAPI] The Odds API error: {e}")
            
        return {
            "ok": False,
            "error": "Foreign API failed or no data",
            "meta": {"source": "the_odds_api", "confidence": 0.0, "mock": False, "stale": True}
        }
