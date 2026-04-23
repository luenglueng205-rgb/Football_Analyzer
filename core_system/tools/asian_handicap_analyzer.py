class AsianHandicapAnalyzer:
    def __init__(self):
        # Simplified conversion table: Euro Odds -> Asian Handicap
        self.conversion_table = [
            (1.10, -2.5), (1.15, -2.0), (1.20, -1.75), (1.25, -1.5),
            (1.35, -1.25), (1.50, -1.0), (1.65, -0.75), (1.85, -0.5),
            (2.10, -0.25), (2.35, 0.0)
        ]

    def _get_theoretical_handicap(self, euro_odds: float) -> float:
        # Find closest match
        closest = min(self.conversion_table, key=lambda x: abs(x[0] - euro_odds))
        return closest[1]

    def analyze_divergence(self, euro_home_odds: float, actual_asian_handicap: float, home_water: float) -> dict:
        theoretical = self._get_theoretical_handicap(euro_home_odds)
        
        # divergence > 0 implies actual handicap is deeper (more negative) than theoretical
        # wait, if actual is -1.25 and theoretical is -1.0, actual - theoretical = -0.25
        divergence = actual_asian_handicap - theoretical
        
        conclusion = "Normal (盘口合理)"
        if divergence > 0.1: # e.g. actual -0.75, theo -1.0 -> 0.25
            conclusion = "Shallow Trap (诱盘/阻筹)"
        elif divergence < -0.1: # e.g. actual -1.25, theo -1.0 -> -0.25
            conclusion = "Deep Support (机构真实看好)"
            
        return {
            "theoretical_handicap": theoretical,
            "actual_handicap": actual_asian_handicap,
            "divergence": divergence,
            "conclusion": conclusion
        }

    def analyze_water_drop(self, opening_water: float, live_water: float) -> dict:
        drop = opening_water - live_water
        return {
            "opening_water": opening_water,
            "live_water": live_water,
            "drop_amplitude": round(drop, 2),
            "is_sharp_drop": drop >= 0.15
        }
