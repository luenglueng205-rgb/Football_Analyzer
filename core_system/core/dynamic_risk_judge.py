import json
import os
import random

class DynamicRiskJudgeAgent:
    """
    100% AI-Native: 动态法官。
    取代了传统系统里由人类设定的风控常量。它会定期读取 PnL 日志，
    自主决定接下来的风险敞口 (Kelly Fraction Limit) 和安全盈亏比。
    """
    def __init__(self, memory_file="global_knowledge_base/memory_core/episodic.json",
                 config_file="standalone_workspace/core/agentic_os/soul_config.json"):
        self.memory_file = memory_file
        self.config_file = config_file

    def _analyze_recent_pnl(self) -> float:
        """分析最近的交易盈亏，计算最大回撤或亏损率"""
        if not os.path.exists(self.memory_file):
            return 0.0
            
        with open(self.memory_file, "r") as f:
            episodes = json.load(f)
            
        recent_episodes = episodes[-10:] # 看最近 10 场
        losses = sum(1 for e in recent_episodes if e.get("PnL", 0) < 0)
        loss_rate = losses / len(recent_episodes) if recent_episodes else 0.0
        
        return loss_rate

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
            print("   -> ⚖️ [Neutral] 市场震荡期，维持中性仓位控制。")
            
        # 写回系统的“灵魂”配置文件
        if os.path.exists(self.config_file):
            with open(self.config_file, "r+") as f:
                config = json.load(f)
                config["risk_tolerance"] = new_max_stake
                config["min_ev"] = new_min_ev
                
                f.seek(0)
                json.dump(config, f, indent=2, ensure_ascii=False)
                f.truncate()
                
        print(f"   -> 🔒 [Update] 已将动态护栏阈值写入系统灵魂 (Max Stake: {new_max_stake:.1%}, Min EV: {new_min_ev})")

if __name__ == "__main__":
    judge = DynamicRiskJudgeAgent()
    judge.adjust_risk_parameters()
