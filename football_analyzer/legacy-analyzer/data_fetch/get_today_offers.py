import requests
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TodayOffersScraper:
    """获取当天体彩各彩种在售赛事"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Origin': 'https://www.sporttery.cn',
            'Referer': 'https://www.sporttery.cn/'
        }
        
    def get_jingcai_matches(self) -> List[Dict]:
        """获取竞彩足球当天在售赛事 (胜平负/让球)"""
        try:
            # 官方API，包含 hhad(让球) 和 had(不让球)
            url = "https://i.sporttery.cn/api/fb_match_info/get_matches?poolcast=2&tzc=1"
            res = requests.get(url, headers=self.headers, timeout=10)
            data = res.json()
            
            if data.get("status", {}).get("code") != 0:
                logger.error("体彩官方API返回异常")
                return []
                
            matches = []
            match_list = data.get("result", {}).get("matchList", [])
            
            for m in match_list:
                # 提取关键信息
                match_info = {
                    "match_id": m.get("matchId"),
                    "match_num_str": m.get("matchNumStr"), # 如 周三001
                    "league": m.get("leagueNameAbbr"),
                    "home_team": m.get("homeTeamNameAbbr"),
                    "away_team": m.get("awayTeamNameAbbr"),
                    "sell_status": m.get("matchStatus"), # Selling
                    "start_time": m.get("matchDate") + " " + m.get("matchTime"),
                    "b_date": m.get("b_date", ""), # 业务日期，用于判断停售
                    "is_single_had": m.get("oddsList", {}).get("had", {}).get("single", 0) == 1,
                    "is_single_hhad": m.get("oddsList", {}).get("hhad", {}).get("single", 0) == 1,
                    "odds": {}
                }
                
                # 提取不让球胜平负
                had = m.get("oddsList", {}).get("had")
                if had:
                    match_info["odds"]["SPF"] = {
                        "h": float(had.get("h", 0)),
                        "d": float(had.get("d", 0)),
                        "a": float(had.get("a", 0))
                    }
                    
                # 提取让球胜平负
                hhad = m.get("oddsList", {}).get("hhad")
                if hhad:
                    match_info["handicap"] = int(hhad.get("goalline", 0))
                    match_info["odds"]["RQSPF"] = {
                        "h": float(hhad.get("h", 0)),
                        "d": float(hhad.get("d", 0)),
                        "a": float(hhad.get("a", 0))
                    }
                    
                matches.append(match_info)
                
            return matches
        except Exception as e:
            logger.error(f"获取竞彩赛事失败: {e}")
            return []

    def get_beidan_matches(self) -> List[Dict]:
        """获取北京单场当天在售赛事 (暂使用模拟数据或第三方备用源)"""
        # 北单官方接口较难直接抓取，这里预留接口，实战可接入 500.com 或 澳客北单页
        # 返回结构与竞彩类似，但需标记 lottery_type = "beidan"
        return [{"note": "北单抓取待接入真实源", "lottery_type": "beidan"}]
        
    def get_traditional_matches(self, issue: str = "") -> Dict:
        """获取传统足彩(如14场/任九)当期对阵"""
        # 传统足彩按期(issue)发售，实战可抓取 500.com 胜负彩页面
        return {"issue": issue, "matches": [], "lottery_type": "traditional"}
        
    def get_today_offers(self, lottery_type: str = "jingcai") -> List[Dict]:
        """统一获取入口"""
        if lottery_type == "jingcai":
            return self.get_jingcai_matches()
        elif lottery_type == "beidan":
            return self.get_beidan_matches()
        elif lottery_type == "traditional":
            return self.get_traditional_matches().get("matches", [])
        else:
            raise ValueError(f"不支持的彩种: {lottery_type}")

if __name__ == "__main__":
    scraper = TodayOffersScraper()
    matches = scraper.get_today_offers("jingcai")
    print(f"成功获取 {len(matches)} 场竞彩在售比赛")
    if matches:
        print(json.dumps(matches[0], ensure_ascii=False, indent=2))
