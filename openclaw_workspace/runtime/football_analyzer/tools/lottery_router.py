import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class LotteryRouter:
    """
    体育彩票三大玩法物理隔离路由器 (Lottery Physical Firewall Router).
    绝对禁止“串台”！根据不同彩种的底层逻辑，强制分流到独立的校验和计算引擎中。
    """

    def __init__(self):
        self.supported_types = ["JINGCAI", "BEIDAN", "ZUCAI"]

    def route_and_validate(self, lottery_type: str, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        核心路由网关。所有 Agent 生成的打票策略必须经过此网关。
        """
        if lottery_type not in self.supported_types:
            raise ValueError(f"🚨 致命错误：未知的彩票类型 {lottery_type}。必须是 {self.supported_types} 之一。")

        logger.info(f"[LotteryRouter] 正在进入 {lottery_type} 专属处理通道...")

        if lottery_type == "JINGCAI":
            return self._process_jingcai(ticket_data)
        elif lottery_type == "BEIDAN":
            return self._process_beidan(ticket_data)
        elif lottery_type == "ZUCAI":
            return self._process_zucai(ticket_data)

    def _process_jingcai(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        【竞彩专属通道】
        特征：固定赔率 (Fixed Odds)，整数让球，支持让平，最大 8 串 1。
        """
        legs = ticket_data.get("legs", [])
        if len(legs) > 8:
            raise ValueError("❌ 竞彩拦截：串关数超过物理上限（8场）。")
            
        for leg in legs:
            if "0.5" in str(leg.get("handicap", "0")):
                raise ValueError(f"❌ 竞彩拦截：竞彩绝对不存在小数让球（如 {leg.get('handicap')}）。")
                
        # 竞彩特有：必须包含明确的固定赔率才能计算 EV
        for leg in legs:
            if "odds" not in leg:
                raise ValueError("❌ 竞彩拦截：缺少固定赔率(Odds)参数，无法计算期望值。")
            odds = leg["odds"]
            if not isinstance(odds, (int, float)) or odds <= 1.0 or odds == float('inf'):
                raise ValueError(f"❌ 竞彩风控拦截：检测到非法赔率数值 ({odds})，涉嫌欺诈或数据错误，直接拒绝。")

        return {"status": "SUCCESS", "channel": "JINGCAI", "message": "竞彩固定赔率物理校验通过。"}

    def _process_beidan(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        【北单专属通道】
        特征：浮动奖池，强制扣除 35% 费用，胜负过关必带 0.5 小数让球，最大 15 串 1。
        """
        legs = ticket_data.get("legs", [])
        play_type = ticket_data.get("play_type", "WDL")
        
        if len(legs) > 15:
            raise ValueError("❌ 北单拦截：串关数超过物理上限（15场）。")

        if play_type == "胜负过关":
            for leg in legs:
                if "0.5" not in str(leg.get("handicap", "0")):
                    raise ValueError("❌ 北单拦截：胜负过关玩法必须带有 0.5 的小数让球，以消除平局。")

        return {"status": "SUCCESS", "channel": "BEIDAN", "message": "北单浮动奖池及小数让球校验通过。"}

    def _process_zucai(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        【传统足彩专属通道】
        特征：绝对没有赔率 (No Odds)！只有全国投注比例。固定 14 场或 9 场。
        """
        legs = ticket_data.get("legs", [])
        play_type = ticket_data.get("play_type", "renjiu") # renjiu, 14_match, etc.
        
        # 足彩绝对不能用 EV = Prob * Odds 计算，因为它没有 Odds！
        for leg in legs:
            if "odds" in leg:
                logger.warning("⚠️ 警告：传统足彩没有固定赔率！传入的 Odds 将被系统强制忽略。")
                
        if play_type == "14_match" and len(legs) != 14:
            raise ValueError(f"❌ 足彩拦截：14场胜负彩必须且只能包含 14 场比赛，当前为 {len(legs)} 场。")
            
        if play_type == "renjiu" and (len(legs) < 9 or len(legs) > 14):
            raise ValueError(f"❌ 足彩拦截：任选九场必须包含 9-14 场比赛，当前为 {len(legs)} 场。")

        return {"status": "SUCCESS", "channel": "ZUCAI", "message": "传统足彩奖池共享模式校验通过。"}
