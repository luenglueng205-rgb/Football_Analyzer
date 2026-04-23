import json
from typing import Dict, Any

class HallucinationGuard:
    """
    2026 AI Native Guardrails: 幻觉防火墙
    绝对禁止 LLM 直接触碰资金或进行自由发挥的数学计算。
    它必须遵守严格的 Pydantic Schema 契约，并通过数学引擎的二次交叉验证。
    """
    def __init__(self):
        # 铁律：最大允许单笔下注比例 (防止 LLM 幻觉梭哈)
        self.MAX_KELLY_STAKE = 0.05 
        # 铁律：最小允许期望值 (防止 LLM 乱买垃圾赔率)
        self.MIN_EV_THRESHOLD = 0.02

    def verify_llm_output(self, llm_response: Dict[str, Any], current_odds: float) -> Dict[str, Any]:
        print("\n==================================================")
        print("🛡️ [Guardrails] 启动 LLM 幻觉防火墙 (Deterministic Audit)...")
        print("==================================================")
        
        # 1. 检查 Schema 完整性 (Schema Enforcement)
        required_keys = ["predicted_win_prob", "confidence_score", "reasoning_hash"]
        for key in required_keys:
            if key not in llm_response:
                print(f"   -> 🚨 [Fatal Error] LLM 幻觉：输出缺失关键字段 '{key}'。")
                return {"status": "REJECTED", "reason": "Schema Violation"}
                
        prob = llm_response["predicted_win_prob"]
        confidence = llm_response["confidence_score"]
        
        # 2. 检查概率边界 (Boundary Check)
        if not (0.01 <= prob <= 0.99):
            print(f"   -> 🚨 [Fatal Error] LLM 幻觉：预测概率 {prob} 超出物理边界。")
            return {"status": "REJECTED", "reason": "Probability Out of Bounds"}
            
        # 3. 确定性数学接管 (Deterministic Math Takeover)
        # 绝对不信任 LLM 算出的 EV，系统自己用公式重算！
        real_ev = (prob * current_odds) - 1.0
        print(f"   -> 🧮 [Math Engine] 重新计算真实期望值 (EV): {real_ev:.4f}")
        
        if real_ev < self.MIN_EV_THRESHOLD:
            print(f"   -> 🛑 [Risk Control] 真实 EV ({real_ev:.4f}) 低于系统安全阈值。拒绝交易。")
            return {"status": "REJECTED", "reason": "Negative or Low EV"}
            
        # 4. 确定性仓位计算 (Kelly Criterion)
        # 绝对不信任 LLM 给出的下注金额，系统自己用凯利公式算！
        # f* = (bp - q) / b  (b = 赔率-1)
        b = current_odds - 1.0
        q = 1.0 - prob
        kelly_fraction = (b * prob - q) / b
        
        # 叠加 LLM 的置信度衰减 (如果 LLM 只有 50% 把握，仓位减半)
        adjusted_kelly = kelly_fraction * confidence
        
        # 最终硬性截断 (Kill Switch)
        final_stake = min(max(0.0, adjusted_kelly), self.MAX_KELLY_STAKE)
        
        print(f"   -> 📉 [Position Sizing] 凯利公式计算基准仓位: {kelly_fraction:.2%}")
        print(f"   -> 📉 [Position Sizing] 置信度衰减后仓位: {adjusted_kelly:.2%}")
        print(f"   -> 🔒 [Hard Limit] 最终安全下注比例: {final_stake:.2%}")
        
        if final_stake <= 0.001:
            print("   -> 🛑 [Risk Control] 计算出安全仓位接近于 0，放弃交易。")
            return {"status": "REJECTED", "reason": "Zero Safe Stake"}

        print("   -> ✅ [Guardrails Passed] LLM 预测已通过所有数学与逻辑审计！")
        return {
            "status": "APPROVED",
            "safe_stake_percentage": final_stake,
            "verified_ev": real_ev
        }

if __name__ == "__main__":
    guard = HallucinationGuard()
    
    # 模拟一个产生幻觉的 LLM 输出 (瞎编了一个极高的概率想梭哈)
    hallucinated_response = {
        "predicted_win_prob": 0.95, # 吹牛
        "confidence_score": 0.90,
        "reasoning_hash": "abc123xyz"
    }
    
    print("\n>>> 测试 1: 拦截危险赔率 (低赔率下的高概率依然 EV 为负) <<<")
    guard.verify_llm_output(hallucinated_response, current_odds=1.02)
    
    print("\n>>> 测试 2: 正常的高价值赔率审计 <<<")
    valid_response = {
        "predicted_win_prob": 0.55, 
        "confidence_score": 0.80,
        "reasoning_hash": "def456uvw"
    }
    guard.verify_llm_output(valid_response, current_odds=2.10)
