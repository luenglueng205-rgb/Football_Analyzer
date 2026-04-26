import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GrandmasterRouter:
    """
    顶级指挥官 (Grandmaster Router)
    负责将统一概率引擎计算出的真实概率，结合官方赔率，路由分发给三大独立玩法专家：
    1. 竞彩狙击手 (Jingcai Sniper)
    2. 北单反指大师 (Beidan Contrarian)
    3. 足彩屠龙者 (Toto 14 Jackpot)
    """
    
    def __init__(self):
        # 竞彩要求的最低期望值 (EV) 门槛，超过此值才值得出手
        self.min_jingcai_ev = 0.05  
        
    def dispatch_matches(self, user_prefs: Dict[str, Any], true_probs: Dict[str, float], official_odds: Dict[str, Any]) -> str:
        """
        核心路由网关：根据胜率和赔率计算期望值，决定最终的物理隔离专家流向。
        
        :param user_prefs: 用户偏好配置 (如是否开启博大奖模式)
        :param true_probs: 真实概率字典 (如: {"home_win": 0.55})
        :param official_odds: 官方赔率字典 (如: {"jingcai_odds": {"home_win": 2.10}})
        :return: 路由决策结果的字符串，供大模型或状态机阅读
        """
        # 提取真实胜率
        # 提取概率
        home_prob = 0.0
        if true_probs:
            if "home_win" in true_probs:
                home_prob = true_probs["home_win"]
            elif "WDL" in true_probs and isinstance(true_probs["WDL"], dict) and "home_win" in true_probs["WDL"]:
                home_prob = true_probs["WDL"]["home_win"]
            elif len(true_probs) > 0:
                first_val = list(true_probs.values())[0]
                if isinstance(first_val, (int, float)):
                    home_prob = first_val
                elif isinstance(first_val, dict) and "home_win" in first_val:
                    home_prob = first_val["home_win"]
                
        # 提取赔率 (兼容旧版和新版多玩法)
        jingcai_odds_dict = official_odds.get("jingcai_odds", {}) if isinstance(official_odds, dict) else {}
        beidan_odds_dict = official_odds.get("beidan_odds", {}) if isinstance(official_odds, dict) else {}
        
        jc_home_odds = 0.0
        if jingcai_odds_dict:
            if "home_win" in jingcai_odds_dict:
                jc_home_odds = jingcai_odds_dict["home_win"]
            elif len(jingcai_odds_dict) > 0:
                jc_home_odds = list(jingcai_odds_dict.values())[0]
        elif beidan_odds_dict:
            if "home_win" in beidan_odds_dict:
                jc_home_odds = beidan_odds_dict["home_win"]
            elif len(beidan_odds_dict) > 0:
                jc_home_odds = list(beidan_odds_dict.values())[0]
        elif isinstance(official_odds, dict):
            if "home_win" in official_odds:
                jc_home_odds = official_odds["home_win"]
            elif len(official_odds) > 0:
                jc_home_odds = list(official_odds.values())[0]
        else:
            jc_home_odds = float(official_odds) if official_odds else 0.0
            
        if jc_home_odds <= 0:
            return "[ROUTE_REJECTED] 拒绝交易: 无效的赔率数据"
            
        # 1. 计算竞彩单关的期望值 (EV)
        # 公式: EV = 真实胜率 * 赔率 - 1
        ev = home_prob * jc_home_odds - 1.0
        
        # 2. 核心路由决策树
        if ev >= self.min_jingcai_ev:
            # 路线 A：庄家开错盘，EV 极高
            # 直接派给竞彩狙击手，优先单关出票
            return f"[JINGCAI_ROUTE] 路由至竞彩专家: 发现价值投注 (EV={ev:.2%})，建议立即单关出票。"
            
        elif ev > -0.15 and home_prob < 0.3:
            # 路线 B：竞彩无利可图，且主队真实胜率极低
            # 意味着大众可能盲目看好名气大的主队，导致北单对应盘口成为“火锅”
            # 路由给北单反指大师，在停售前做空热门
            return f"[BEIDAN_ROUTE] 路由至北单专家: 主队胜率极低 ({home_prob:.2%}) 且可能大热，建议延迟至停售前5分钟做空对手盘。"
            
        elif user_prefs.get("jackpot_mode", False) or ev <= -0.15:
            # 路线 C：比赛单场实在太毒 (EV极低，被疯狂抽水)，或者用户主动开启了博冷模式
            # 这种比赛单买必亏，但非常适合放入足彩 14 场的冷门备选库中过滤 99% 的散户
            return f"[TOTO14_ROUTE] 路由至足彩专家: 单场无投注价值 (EV={ev:.2%})，放入足彩14场作为博冷过滤素材。"
            
        else:
            # 路线 D：食之无味，弃之可惜的“垃圾时间”比赛
            return f"[NO_ACTION] 拒绝交易: 比赛毫无价值 (EV={ev:.2%})，建议空仓观望。"
