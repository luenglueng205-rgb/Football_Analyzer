from typing import List, Dict, Any

from standalone_workspace.core.recommendation_schema import RecommendationSchemaAdapter

class SmartBetSelector:
    """
    智能选票器。支持竞彩(固定赔率)、北单(65%返奖率)和传统足彩(无赔率概率优势)。
    """
    def __init__(self, min_ev_threshold: float = 1.05, min_edge_threshold: float = 0.15):
        self.min_ev_threshold = min_ev_threshold
        self.min_edge_threshold = min_edge_threshold # 足彩特有：真实胜率与大众支持率的最小差值

    def extract_value_bets(self, matches_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        value_bets = []
        
        for match in matches_data:
            match_id = match.get("match_id")
            lottery_type = match.get("lottery_type", "JINGCAI").upper()
            markets = match.get("markets", {})
            
            for market_name, options in markets.items():
                for selection, data in options.items():
                    prob = data.get("prob", 0.0)
                    
                    if lottery_type == "ZUCAI":
                        support_rate = data.get("support_rate", 0.0)
                        edge = prob - support_rate
                        
                        if edge >= self.min_edge_threshold:
                            value_bets.append({
                                "match_id": match_id,
                                "lottery_type": lottery_type,
                                "market": market_name,
                                "selection": selection,
                                "prob": round(prob, 4),
                                "support_rate": support_rate,
                                "probability_edge": round(edge, 4),
                                "ev": 0.0, # 足彩无直接EV
                                "desc": f"[{match_id}] ZUCAI {market_name} - {selection} (胜率:{prob:.1%}, 大众:{support_rate:.1%}, 优势:{edge:.1%})"
                            })
                    else:
                        odds = data.get("odds", 0.0)
                        ev = odds * prob
                        
                        # 北单必须扣除 35% 奖池抽水
                        if lottery_type == "BEIDAN":
                            ev = ev * 0.65
                            
                        if ev >= self.min_ev_threshold:
                            value_bets.append({
                                "match_id": match_id,
                                "lottery_type": lottery_type,
                                "market": market_name,
                                "selection": selection,
                                "odds": odds,
                                "prob": round(prob, 4),
                                "ev": round(ev, 4),
                                "desc": f"[{match_id}] {lottery_type} {market_name} - {selection} (赔率:{odds}, 胜率:{prob:.1%}, EV:{ev:.2f})"
                            })
                        
        value_bets.sort(key=lambda x: x.get("probability_edge", x["ev"]), reverse=True)
        return value_bets

    def extract_value_bets_schema(self, matches_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        value_bets = self.extract_value_bets(matches_data)
        return RecommendationSchemaAdapter.from_smart_bet_selector_output(value_bets).to_dict()
