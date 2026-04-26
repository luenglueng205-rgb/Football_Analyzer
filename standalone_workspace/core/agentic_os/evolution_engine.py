import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from tools.paths import knowledge_base_dir
except ImportError:
    knowledge_base_dir = lambda *args: Path(__file__).resolve().parent.parent.parent / "workspace" / "orchestrator" / "knowledge_base"


_AGENTIC_OS_DIR = Path(__file__).resolve().parent
_DEFAULT_SEMANTIC_FILE = Path(knowledge_base_dir("memory_core", "semantic_truth.json"))
_DEFAULT_CONFIG_FILE = _AGENTIC_OS_DIR / "soul_config.json"


class EvolutionEngine:
    """
    2026 Agentic OS - 进化引擎 (Self-Modification Engine)
    负责读取海马体的"真理"，并动态修改系统的核心配置文件或代码。
    """
    def __init__(self, semantic_file=None, config_file=None, event_bus=None):
        self.semantic_file = str(Path(semantic_file).expanduser()) if semantic_file else str(_DEFAULT_SEMANTIC_FILE)
        self.config_file = str(Path(config_file).expanduser()) if config_file else str(_DEFAULT_CONFIG_FILE)

        # EventBus integration
        self._event_bus = event_bus
        if self._event_bus is None:
            try:
                from core.event_bus import EventBus as _EB
                self._event_bus = _EB()
            except ImportError:
                pass
        if self._event_bus is not None:
            # subscribe is async, schedule it safely
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._event_bus.subscribe("workflow.complete", self.on_workflow_complete))
            except RuntimeError:
                pass

        self._init_config()

    def on_workflow_complete(self, data: Dict[str, Any]) -> None:
        """收到 workflow 完成事件时，读取 PnL 并更新 active_rules"""
        pnl = data.get("pnl", 0)
        if pnl < 0:
            # Negative PnL triggers evolution check
            self.trigger_evolution()

    def _init_config(self):
        config_path = Path(self.config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if not config_path.exists():
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({
                    "core_directives": ["绝对理性", "EV>0才交易", "保住本金"],
                    "risk_tolerance": 0.05,
                    "active_rules": []
                }, f, indent=2, ensure_ascii=False)

    def trigger_evolution(self):
        """执行自我手术：将真理写入执行潜意识"""
        print("   [Evolution] 🧬 触发自我手术 (Self-Modification)...")
        semantic_path = Path(self.semantic_file)
        config_path = Path(self.config_file)
        if not semantic_path.exists():
            return

        with open(semantic_path, "r", encoding="utf-8") as f:
            semantic = json.load(f)

        with open(config_path, "r+", encoding="utf-8") as f:
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
