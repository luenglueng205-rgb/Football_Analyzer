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

    def _normalize_play_type(self, lottery_type: str, play_type: Any) -> str:
        lt = str(lottery_type or "").upper()
        s = str(play_type or "").strip()
        up = s.upper()
        if lt == "JINGCAI":
            if up in {"JINGCAI_WDL", "WDL", "1X2"}:
                return "WDL"
            if up in {"JINGCAI_HANDICAP_WDL", "HANDICAP_WDL", "HANDICAP", "RQ"}:
                return "HANDICAP"
            if up in {"JINGCAI_GOALS", "GOALS", "TOTAL_GOALS"}:
                return "GOALS"
            if up in {"JINGCAI_CS", "CS", "CORRECT_SCORE"}:
                return "CS"
            if up in {"JINGCAI_HTFT", "HTFT"}:
                return "HTFT"
            if up in {"JINGCAI_MIXED_PARLAY", "MIXED_PARLAY", "MIXED"}:
                return "MIXED_PARLAY"
            return up or "WDL"
        if lt == "BEIDAN":
            if up in {"BEIDAN_WDL", "WDL", "1X2"}:
                return "WDL"
            if up in {"BEIDAN_SFGG", "SFGG", "胜负过关", "BEIDAN_HANDICAP_WDL"}:
                return "SFGG"
            if up in {"BEIDAN_UP_DOWN_ODD_EVEN", "UP_DOWN_ODD_EVEN", "SXDS", "UDOE"}:
                return "UP_DOWN_ODD_EVEN"
            if up in {"BEIDAN_GOALS", "GOALS", "TOTAL_GOALS"}:
                return "GOALS"
            if up in {"BEIDAN_HTFT", "HTFT"}:
                return "HTFT"
            if up in {"BEIDAN_CS", "CS", "CORRECT_SCORE"}:
                return "CS"
            return up or "WDL"
        if lt == "ZUCAI":
            if up in {"ZUCAI_14_MATCH", "14_MATCH", "14MATCH", "14"}:
                return "14_match"
            if up in {"ZUCAI_RENJIU", "RENJIU", "RX9", "9"}:
                return "renjiu"
            if up in {"ZUCAI_6_HTFT", "6_HTFT", "6HTFT"}:
                return "6_htft"
            if up in {"ZUCAI_4_GOALS", "4_GOALS", "4GOALS"}:
                return "4_goals"
            low = s.lower()
            if low in {"14_match", "renjiu", "6_htft", "4_goals"}:
                return low
            return low or "renjiu"
        return up or "WDL"

    def route_and_validate(self, lottery_type: str, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        核心路由网关。所有 Agent 生成的打票策略必须经过此网关。
        """
        lt = str(lottery_type or "").upper()
        if lt not in self.supported_types:
            raise ValueError(f"🚨 致命错误：未知的彩票类型 {lottery_type}。必须是 {self.supported_types} 之一。")

        normalized_ticket = dict(ticket_data or {})
        normalized_ticket["play_type"] = self._normalize_play_type(lt, normalized_ticket.get("play_type"))
        logger.info(f"[LotteryRouter] 正在进入 {lt} 专属处理通道...")

        if lt == "JINGCAI":
            return self._process_jingcai(normalized_ticket)
        if lt == "BEIDAN":
            return self._process_beidan(normalized_ticket)
        if lt == "ZUCAI":
            return self._process_zucai(normalized_ticket)
        raise ValueError(f"🚨 致命错误：未知的彩票类型 {lottery_type}。必须是 {self.supported_types} 之一。")

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
        play_type = self._normalize_play_type("BEIDAN", ticket_data.get("play_type", "WDL"))
        
        if len(legs) > 15:
            raise ValueError("❌ 北单拦截：串关数超过物理上限（15场）。")

        if play_type == "SFGG":
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
        play_type = self._normalize_play_type("ZUCAI", ticket_data.get("play_type", "renjiu"))
        
        # 足彩绝对不能用 EV = Prob * Odds 计算，因为它没有 Odds！
        for leg in legs:
            if "odds" in leg:
                logger.warning("⚠️ 警告：传统足彩没有固定赔率！传入的 Odds 将被系统强制忽略。")
                
        if play_type == "14_match" and len(legs) != 14:
            raise ValueError(f"❌ 足彩拦截：14场胜负彩必须且只能包含 14 场比赛，当前为 {len(legs)} 场。")
            
        if play_type == "renjiu" and (len(legs) < 9 or len(legs) > 14):
            raise ValueError(f"❌ 足彩拦截：任选九场必须包含 9-14 场比赛，当前为 {len(legs)} 场。")

        if play_type == "6_htft" and len(legs) != 6:
            raise ValueError(f"❌ 足彩拦截：6场半全场必须且只能包含 6 场比赛，当前为 {len(legs)} 场。")

        if play_type == "4_goals" and len(legs) != 4:
            raise ValueError(f"❌ 足彩拦截：4场进球彩必须且只能包含 4 场比赛，当前为 {len(legs)} 场。")

        return {"status": "SUCCESS", "channel": "ZUCAI", "message": "传统足彩奖池共享模式校验通过。"}
