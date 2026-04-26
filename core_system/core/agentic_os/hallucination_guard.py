import json
from pathlib import Path
from typing import Dict, Any


_DEFAULT_CONFIG_FILE = Path(__file__).resolve().with_name("soul_config.json")

class HallucinationGuard:
    """
    100% AI-Native Guardrails: 动态幻觉防火墙
    不再使用人类硬编码的 `MAX_KELLY_STAKE = 0.05`。
    所有的风控阈值由系统的灵魂 (soul_config.json) 动态读取，实现风控自治。
    """
    def __init__(self, config_file=None):
        self.config_file = Path(config_file).expanduser() if config_file else _DEFAULT_CONFIG_FILE
        self.max_kelly_stake = 0.02 # 默认极度保守
        self.min_ev_threshold = 0.05
        self._load_dynamic_config()

    def _load_dynamic_config(self):
        """AI-Native: 动态加载由 Dynamic Judge 调整的风控阈值"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 从配置文件读取 AI 设定的风险容忍度
                    self.max_kelly_stake = config.get("risk_tolerance", 0.02)
                    self.min_ev_threshold = config.get("min_ev", 0.02)
            except Exception as e:
                print(f"   [Guardrails] 无法加载动态配置: {e}，回退至安全默认值。")

    def verify_llm_output(self, llm_response: Dict[str, Any], current_odds: float) -> Dict[str, Any]:
        print("\n==================================================")
        print(f"🛡️ [Guardrails] 启动动态幻觉防火墙 (Max Stake: {self.max_kelly_stake:.1%})...")
        print("==================================================")
        
        # 1. 检查 Schema 完整性 (Schema Enforcement)
        # Core required fields (reasoning_hash is optional for backward compatibility)
        required_keys = ["predicted_win_prob", "confidence_score"]
        optional_keys = ["reasoning_hash"]
        for key in required_keys:
            if key not in llm_response:
                print(f"   -> 🚨 [Fatal Error] LLM 幻觉：输出缺失关键字段 '{key}'。")
                return {"status": "REJECTED", "reason": "Schema Violation"}

        # Warn about missing optional fields but don't reject
        for key in optional_keys:
            if key not in llm_response:
                print(f"   -> ⚠️ [Warning] LLM 输出缺少可选字段 '{key}'，已忽略。")
                
        prob = llm_response["predicted_win_prob"]
        confidence = llm_response["confidence_score"]
        
        # 2. 检查概率边界 (Boundary Check)
        if not (0.01 <= prob <= 0.99):
            print(f"   -> 🚨 [Fatal Error] LLM 幻觉：预测概率 {prob} 超出物理边界。")
            return {"status": "REJECTED", "reason": "Probability Out of Bounds"}
            
        # 3. 确定性数学接管 (Deterministic Math Takeover)
        real_ev = (prob * current_odds) - 1.0
        print(f"   -> 🧮 [Math Engine] 重新计算真实期望值 (EV): {real_ev:.4f}")
        
        if real_ev < self.min_ev_threshold:
            print(f"   -> 🛑 [Risk Control] 真实 EV ({real_ev:.4f}) 低于动态安全阈值 ({self.min_ev_threshold})。拒绝交易。")
            return {"status": "REJECTED", "reason": "Negative or Low EV"}
            
        # 4. 确定性仓位计算 (Kelly Criterion)
        b = current_odds - 1.0
        q = 1.0 - prob
        kelly_fraction = (b * prob - q) / b
        
        adjusted_kelly = kelly_fraction * confidence
        
        # 使用 AI 动态设定的最大仓位进行截断
        final_stake = min(max(0.0, adjusted_kelly), self.max_kelly_stake)
        
        print(f"   -> 📉 [Position Sizing] 凯利公式计算基准仓位: {kelly_fraction:.2%}")
        print(f"   -> 📉 [Position Sizing] 置信度衰减后仓位: {adjusted_kelly:.2%}")
        print(f"   -> 🔒 [Dynamic Limit] 最终安全下注比例: {final_stake:.2%} (受限于 AI 风控阀值)")
        
        if final_stake <= 0.001:
            print("   -> 🛑 [Risk Control] 计算出安全仓位接近于 0，放弃交易。")
            return {"status": "REJECTED", "reason": "Zero Safe Stake"}

        print("   -> ✅ [Guardrails Passed] LLM 预测已通过动态审计！")
        return {
            "status": "APPROVED",
            "safe_stake_percentage": final_stake,
            "verified_ev": real_ev
        }

if __name__ == "__main__":
    guard = HallucinationGuard()
    valid_response = {"predicted_win_prob": 0.55, "confidence_score": 0.80, "reasoning_hash": "def456uvw"}
    guard.verify_llm_output(valid_response, current_odds=2.10)
