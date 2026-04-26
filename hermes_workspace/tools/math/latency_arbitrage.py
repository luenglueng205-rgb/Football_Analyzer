from typing import Dict, Any

def detect_latency_arbitrage(jingcai_odds: float, pinnacle_odds: float, pinnacle_margin: float = 0.025) -> Dict[str, Any]:
    """
    赔率时差套利监控器 (Latency Arbitrage Monitor)。
    对比竞彩固定赔率与国际主流公司（如平博 Pinnacle）的即时赔率。
    如果竞彩赔率高于国际市场“去抽水”后的公平赔率，说明竞彩操盘手反应滞后，存在绝对套利空间。
    """
    if jingcai_odds <= 1.0 or pinnacle_odds <= 1.0:
        return {"is_arbitrage": False, "alert": "无效赔率"}
        
    # 计算 Pinnacle 的真实概率 (剔除 2.5% 的平博标准抽水)
    # Fair Prob = (1 / Pinnacle Odds) * (1 - Margin) 简化计算
    fair_prob = (1.0 / pinnacle_odds) * (1.0 - pinnacle_margin)
    
    # 计算在竞彩下注的期望值 EV
    ev = (fair_prob * jingcai_odds) - 1.0
    
    # 只要 EV > 0，就是绝对的降维打击套利
    is_arbitrage = ev > 0.02 # 设定 2% 的最小摩擦阈值
    
    alert = ""
    if is_arbitrage:
        alert = f"💰 时差套利触发！平博赔率已跌至 {pinnacle_odds} (真实胜率 {fair_prob:.1%})，而竞彩仍停留在 {jingcai_odds}。立即买入，期望收益率: {ev:.2%}！"
    else:
        alert = "无套利空间，竞彩赔率处于正常被抽水状态。"
        
    return {
        "is_arbitrage": is_arbitrage,
        "fair_prob": round(fair_prob, 3),
        "ev": round(ev, 3),
        "alert": alert
    }
