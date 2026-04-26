from typing import Dict, Any

def identify_low_odds_trap(jingcai_odds: float, true_prob: float, vig: float = 0.89) -> Dict[str, Any]:
    """
    泊松分布低赔诱盘识别器 (Low Odds Trap Identifier)。
    专门识别竞彩中低于 1.40 的“蚊子肉”毒药选项，防止串关爆仓。
    """
    if jingcai_odds <= 1.0:
        return {"is_trap": True, "warning": "无效赔率"}
        
    implied_prob = vig / jingcai_odds
    
    # 定义陷阱逻辑：
    # 1. 赔率低于 1.40（极度热门）
    # 2. 庄家给出的隐含胜率 远大于 我们算出的真实胜率 (差值 > 10%)
    is_low_odds = jingcai_odds < 1.40
    prob_divergence = implied_prob - true_prob
    
    is_trap = is_low_odds and (prob_divergence > 0.10)
    
    warning = ""
    if is_trap:
        warning = f"🚨 蚊子肉陷阱警告！竞彩开出 {jingcai_odds} 极低赔率诱导串关，其隐含胜率为 {implied_prob:.1%}，但真实胜率仅为 {true_prob:.1%}。严重高估，坚决规避！"
    elif is_low_odds:
        warning = f"⚠️ 赔率较低 ({jingcai_odds})，但真实胜率 ({true_prob:.1%}) 足以支撑，可作串关稳胆。"
    else:
        warning = "✅ 赔率处于正常区间，无明显诱盘迹象。"
        
    return {
        "is_trap": is_trap,
        "implied_prob": round(implied_prob, 3),
        "true_prob": round(true_prob, 3),
        "divergence": round(prob_divergence, 3),
        "warning": warning
    }
