from typing import Dict, Any

def detect_betfair_anomaly(odds: float, volume_percentage: float) -> Dict[str, Any]:
    """
    必发交易量异常探测器 (Betfair Volume Anomaly Detector)。
    对比某选项的“赔率隐含概率”与“实际成交资金比例”。
    专门用于传统足彩（任九）和北单的“冷热防爆”与反向套利。
    """
    if odds <= 1.0 or volume_percentage < 0 or volume_percentage > 1:
        return {"is_anomaly": False, "analysis": "无效数据"}
        
    implied_prob = 1.0 / odds
    
    # 计算资金热度偏差 (Volume Divergence)
    divergence = volume_percentage - implied_prob
    
    is_anomaly = False
    analysis = ""
    suggested_action = "OBSERVE"
    
    if divergence > 0.25:
        # 资金极度集中，但赔率并未反映出这种胜率（即赔率居高不下）
        # 典型的“主力派发 / 散户接盘”陷阱，俗称大热必死
        is_anomaly = True
        analysis = f"🚨 主力派发警告！成交量占比高达 {volume_percentage:.1%}，但赔率维持在 {odds} (概率仅 {implied_prob:.1%})。存在巨大的卖单(Lay)压制，大热必死。"
        suggested_action = "FADE" # 建议反买（防冷）
        
    elif divergence < -0.15 and implied_prob > 0.40:
        # 赔率很低（看似稳赢），但市场上根本没人买
        # 典型的“诱盘冷遇”或“聪明钱撤退”
        is_anomaly = True
        analysis = f"🥶 聪明钱冷遇！赔率仅 {odds} (概率 {implied_prob:.1%})，但成交量极度萎靡 ({volume_percentage:.1%})。庄家可能在诱导串关，缺乏主力资金背书。"
        suggested_action = "FADE"
        
    else:
        analysis = f"✅ 资金与赔率分布合理。隐含概率 {implied_prob:.1%}，成交比例 {volume_percentage:.1%}。"
        suggested_action = "FOLLOW" if implied_prob > 0.5 else "OBSERVE"
        
    return {
        "is_anomaly": is_anomaly,
        "implied_prob": round(implied_prob, 3),
        "divergence": round(divergence, 3),
        "analysis": analysis,
        "suggested_action": suggested_action
    }
