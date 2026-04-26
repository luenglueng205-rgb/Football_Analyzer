import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from tools.paths import knowledge_base_dir
except ImportError:
    knowledge_base_dir = lambda *args: Path(__file__).resolve().parent.parent.parent / "workspace" / "orchestrator" / "knowledge_base"

logger = logging.getLogger(__name__)

_AGENTIC_OS_DIR = Path(__file__).resolve().parent / "agentic_os"
_DEFAULT_MEMORY_FILE = Path(knowledge_base_dir("memory_core", "episodic.json"))
_DEFAULT_CONFIG_FILE = _AGENTIC_OS_DIR / "soul_config.json"


class DynamicRiskJudgeAgent:
    """
    100% AI-Native: 动态法官。
    取代了传统系统里由人类设定的风控常量。它会定期读取 PnL 日志，
    自主决定接下来的风险敞口 (Kelly Fraction Limit) 和安全盈亏比。
    """
    def __init__(self, memory_file=None, config_file=None, event_bus=None):
        self.memory_file = Path(memory_file).expanduser() if memory_file else _DEFAULT_MEMORY_FILE
        self.config_file = Path(config_file).expanduser() if config_file else _DEFAULT_CONFIG_FILE

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

    def on_workflow_complete(self, data: Dict[str, Any]) -> None:
        """收到 workflow 完成事件时，调用 adjust_risk_parameters 更新风控参数"""
        self.adjust_risk_parameters()

    def _analyze_recent_pnl(self) -> float:
        """分析最近的交易盈亏，计算最大回撤或亏损率"""
        if not self.memory_file.exists():
            return 0.0
            
        with open(self.memory_file, "r", encoding="utf-8") as f:
            episodes = json.load(f)
            
        recent_episodes = episodes[-10:] # 看最近 10 场
        losses = sum(1 for e in recent_episodes if e.get("PnL", 0) < 0)
        loss_rate = losses / len(recent_episodes) if recent_episodes else 0.0
        
        return loss_rate

    def _atomic_write_config(self, config: dict) -> None:
        """
        原子写入 soul_config.json。
        使用 tempfile + os.replace 确保并发安全，即使多个 Agent 同时写也不会产生半截 JSON。
        """
        config_dir = self.config_file.parent
        config_dir.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(dir=config_dir, suffix=".tmp", prefix="soul_config_")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, self.config_file)  # 原子操作，POSIX 保证
            except Exception:
                # 写入失败时清理临时文件
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            logger.error(f"soul_config.json 写入失败: {e}")
            raise

    def adjust_risk_parameters(self):
        print("==================================================")
        print("⚖️ [Agentic Risk Judge] 启动 AI 动态风控参数评估...")
        print("==================================================")
        
        loss_rate = self._analyze_recent_pnl()
        print(f"   -> 📊 [Audit] 近期交易胜率评估: 亏损率达 {loss_rate:.1%}")
        
        # 动态调整逻辑 (模拟大模型根据市场情况做出的风控决策)
        new_max_stake = 0.05
        new_min_ev = 0.02
        
        if loss_rate > 0.5:
            print("   -> 🚨 [Warning] 检测到严重回撤！进入极度防御模式。")
            new_max_stake = 0.01  # 仓位降到 1%
            new_min_ev = 0.08     # 只有极高利润才出手
        elif loss_rate < 0.2:
            print("   -> 📈 [Aggressive] 市场顺风期！放宽风险敞口，扩大盈利。")
            new_max_stake = 0.08  # 仓位放宽到 8%
            new_min_ev = 0.01     # 捕捉微小利润
        else:
            # ✅ 修复 P2-4：中性区同样需要写入默认值，与其他分支行为一致
            print("   -> ⚖️ [Neutral] 市场震荡期，维持中性仓位控制。")
            new_max_stake = 0.05
            new_min_ev = 0.02
            
        # ✅ 修复 P1-1：改用原子写入，防止并发场景下配置文件损坏
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {}

        config["risk_tolerance"] = new_max_stake
        config["min_ev"] = new_min_ev
        self._atomic_write_config(config)
                
        print(f"   -> 🔒 [Update] 已将动态护栏阈值写入系统灵魂 (Max Stake: {new_max_stake:.1%}, Min EV: {new_min_ev})")


if __name__ == "__main__":
    judge = DynamicRiskJudgeAgent()
    judge.adjust_risk_parameters()
