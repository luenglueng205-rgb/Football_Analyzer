import json
import os

class EvolutionEngine:
    """
    2026 Agentic OS - 进化引擎 (Self-Modification Engine)
    负责读取海马体的“真理”，并动态修改系统的核心配置文件或代码。
    """
    def __init__(self, semantic_file="global_knowledge_base/memory_core/semantic_truth.json"):
        self.semantic_file = semantic_file
        self.config_file = "standalone_workspace/core/agentic_os/soul_config.json"
        self._init_config()

    def _init_config(self):
        if not os.path.exists(self.config_file):
            with open(self.config_file, "w") as f:
                json.dump({
                    "core_directives": ["绝对理性", "EV>0才交易", "保住本金"],
                    "risk_tolerance": 0.05,
                    "active_rules": []
                }, f, indent=2, ensure_ascii=False)

    def trigger_evolution(self):
        """执行自我手术：将真理写入执行潜意识"""
        print("   [Evolution] 🧬 触发自我手术 (Self-Modification)...")
        if not os.path.exists(self.semantic_file):
            return

        with open(self.semantic_file, "r") as f:
            semantic = json.load(f)

        with open(self.config_file, "r+") as f:
            config = json.load(f)
            
            # 更新风险容忍度
            config["risk_tolerance"] = semantic["risk_tolerance"]
            
            # 挂载新真理为活跃规则
            for truth in semantic["truths"]:
                if truth not in config["active_rules"]:
                    config["active_rules"].append(truth)
                    print(f"   [Evolution] ⚙️ 已将新真理写入系统活跃规则库: {truth[:20]}...")
            
            f.seek(0)
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.truncate()
            
        print("   [Evolution] ✅ 进化完成。系统已被重塑。")

if __name__ == "__main__":
    engine = EvolutionEngine()
    engine.trigger_evolution()
