from typing import List, Dict, Any

class SmartBetSelector:
    """
    智能选票器。负责遍历所有玩法，砍掉低赔陷阱，只保留期望值 (EV) > 1 的价值投注。
    """
    def __init__(self, min_ev_threshold: float = 1.05):
        # 设定最低期望值门槛，1.05 表示每投注 100 元，理论预期回报 105 元
        self.min_ev_threshold = min_ev_threshold

    def extract_value_bets(self, matches_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        value_bets = []
        
        for match in matches_data:
            match_id = match.get("match_id")
            markets = match.get("markets", {})
            
            # 遍历该场比赛的所有玩法和选项
            for market_name, options in markets.items():
                for selection, data in options.items():
                    odds = data.get("odds", 0.0)
                    prob = data.get("prob", 0.0)
                    
                    ev = odds * prob
                    
                    if ev >= self.min_ev_threshold:
                        value_bets.append({
                            "match_id": match_id,
                            "market": market_name,
                            "selection": selection,
                            "odds": odds,
                            "prob": round(prob, 4),
                            "ev": round(ev, 4),
                            "desc": f"[{match_id}] {market_name} - {selection} (赔率:{odds}, 胜率:{prob:.1%}, EV:{ev:.2f})"
                        })
                        
        # 按照 EV 从高到低排序，优先推荐最有价值的单子
        value_bets.sort(key=lambda x: x["ev"], reverse=True)
        return value_bets
