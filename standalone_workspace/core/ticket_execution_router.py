import json

class TicketExecutionRouter:
    """
    100% AI-Native: 出票执行路由 (Ticket Builder)
    接收 Omni-Pricer 计算出的全玩法真实概率，并对比官方实时赔率。
    AI 借此找出价值最大的具体玩法，并组装成符合体彩规则的彩票单 (Ticket)。
    """
    def __init__(self):
        self.min_ev = 0.05

    def route_best_ticket(self, match_id: str, true_probs: dict, real_time_odds: dict):
        print("==================================================")
        print(f"🎫 [Ticket Router] 正在跨 16 种玩法搜索最高 EV 选项...")
        print("==================================================")
        
        best_option = None
        highest_ev = -1.0
        
        # 扫描所有玩法寻找最高期望值 (EV)
        for market, prob in true_probs.items():
            # 排除非标量概率字典（如比分/总进球，需要展平）
            if isinstance(prob, dict):
                for sub_key, sub_prob in prob.items():
                    odds_key = f"{market}_{sub_key}"
                    odds = real_time_odds.get(odds_key, 0)
                    if odds > 0:
                        ev = (sub_prob * odds) - 1.0
                        if ev > highest_ev:
                            highest_ev = ev
                            best_option = (odds_key, sub_prob, odds, ev)
            else:
                odds = real_time_odds.get(market, 0)
                if odds > 0:
                    ev = (prob * odds) - 1.0
                    if ev > highest_ev:
                        highest_ev = ev
                        best_option = (market, prob, odds, ev)
                        
        if highest_ev < self.min_ev:
            print(f"   -> 🛑 放弃比赛 {match_id}: 全盘 16 种玩法扫描完毕，未发现 EV > {self.min_ev} 的选项。")
            return None
            
        market_name, prob, odds, ev = best_option
        print(f"   -> 💎 [Alpha Found] 跨玩法价值发现！最高 EV 出现在玩法: 【{market_name}】")
        print(f"      真实胜率: {prob:.2%} | 官方赔率: {odds} | 期望收益 (EV): +{ev:.2%}")
        
        # 路由到具体体彩实体票 (Single vs Parlay)
        # 简化逻辑：如果在北单 (SXDS)，则出北单票；如果在竞彩，出竞彩票。
        if "SXDS" in market_name:
            print("   -> 🖨️ [Execution] 路由至【北京单场】出票机 (注意：北单需扣除 35% 公益金再算最终收益)。")
        else:
            print("   -> 🖨️ [Execution] 路由至【竞彩足球】出票机 (优先单关，无单关则压入 2串1 备选池)。")
            
        return best_option

if __name__ == "__main__":
    # 模拟官方赔率 (假设竞彩主胜被严重压低，但总进球 3 球的赔率开高了)
    mock_official_odds = {
        "HAD_H": 1.35, # 竞彩极低主胜
        "HHAD_-1_H": 2.10,
        "TTG_3": 4.20, # 官方总进球3球赔率开得很高
        "SXDS_ShangDan": 3.80
    }
    
    # 假设 AI 算出的真实概率
    mock_true_probs = {
        "HAD_H": 0.70, # EV: 0.7*1.35-1 = -0.055 (负期望！)
        "HHAD_-1_H": 0.45, # EV: 0.45*2.10-1 = -0.055 (负期望！)
        "TTG": {"3": 0.28}, # EV: 0.28*4.20-1 = +0.176 (极高正期望！)
        "SXDS": {"ShangDan": 0.25}
    }
    
    router = TicketExecutionRouter()
    router.route_best_ticket("ARS_vs_CHE", mock_true_probs, mock_official_odds)
