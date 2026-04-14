import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class MatchPreFilter:
    """
    周末洪峰初筛漏斗：在不消耗大模型 Token 的前提下，快速过滤掉无投资价值的比赛。
    """
    def __init__(self):
        # 预设五大联赛等高价值赛事白名单，或者通过黑名单过滤
        self.top_leagues = ["英超", "西甲", "意甲", "德甲", "法甲", "欧冠", "欧罗巴"]
        self.ignore_keywords = ["女足", "青年", "U21", "U19", "友谊赛", "后备"]

    def is_high_value_match(self, match: Dict) -> bool:
        """
        判断比赛是否值得动用昂贵的 SyndicateOS 进行深度分析
        """
        home = match.get("home_team", "")
        away = match.get("away_team", "")
        league = match.get("league", "")
        
        # 1. 过滤野鸡赛事关键字
        combined_text = f"{home} {away} {league}"
        for kw in self.ignore_keywords:
            if kw in combined_text:
                logger.info(f"过滤: {home} vs {away} (原因: 包含忽略关键字 '{kw}')")
                return False
                
        # 这里还可以加入初步的赔率过滤（比如调用一次免费 API，发现胜赔 1.05 直接抛弃）
        # 出于演示，我们假设经过关键字过滤的都是有价值的
        return True

    def filter_matches(self, matches: List[Dict]) -> List[Dict]:
        """批量过滤"""
        return [m for m in matches if self.is_high_value_match(m)]
