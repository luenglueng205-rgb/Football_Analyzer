import random
import json
import time

class AgentGenome:
    def __init__(self, agent_id, risk_tolerance=None, min_ev=None, market_bias=None):
        self.agent_id = agent_id
        # 基因序列
        self.risk_tolerance = risk_tolerance if risk_tolerance else random.uniform(0.01, 0.10)
        self.min_ev = min_ev if min_ev else random.uniform(0.01, 0.15)
        # 偏好的彩票玩法: 0=竞彩, 1=北单, 2=足彩
        self.market_bias = market_bias if market_bias else random.randint(0, 2)
        
        self.balance = 1000.0 # 初始生命能量 (USD)
        self.is_alive = True

    def simulate_trading_week(self):
        """模拟在斗兽场里交易一周的盈亏"""
        if not self.is_alive: return
        
        # 激进的基因容易暴富也容易爆仓
        volatility = self.risk_tolerance * 10
        # 如果追求高 EV，出手次数少，方差大
        ev_penalty = self.min_ev * 5
        
        # 随机漫步加上基因偏误
        daily_returns = [random.normalvariate(0.02 - ev_penalty, volatility) for _ in range(7)]
        
        for r in daily_returns:
            self.balance *= (1 + r)
            if self.balance < 100.0: # 饿死线
                self.is_alive = False
                break

class SwarmEvolutionEngine:
    """
    2026 AI-Native: 达尔文虫群繁衍引擎 (Self-Replicating Swarm)
    不再依赖单一的策略调整，而是生成 100 个微型变异 Agent 放入沙盒厮杀。
    亏光的直接销毁，赚最多的进行基因交配，繁衍出下一代。
    """
    def __init__(self, population_size=50):
        self.population_size = population_size
        self.population = [AgentGenome(f"Agent_Gen1_{i}") for i in range(population_size)]

    def run_evolution_epoch(self):
        print("==================================================")
        print(f"🧬 [Swarm Evolution] 启动达尔文斗兽场，当前种群数量: {len(self.population)} 个微型 Agent")
        print("==================================================")
        
        # 1. 模拟生存竞争 (Paper Trading)
        print("   -> ⚔️ [Survival] 正在模拟一周高频交易厮杀...")
        for agent in self.population:
            agent.simulate_trading_week()
            
        # 2. 清理尸体 (Natural Selection)
        survivors = [a for a in self.population if a.is_alive]
        dead_count = self.population_size - len(survivors)
        print(f"   -> ☠️ [Selection] {dead_count} 个 Agent 跌破生存线，已被系统无情销毁 (Kill Process)。")
        
        # 按资金量排序
        survivors.sort(key=lambda x: x.balance, reverse=True)
        
        if not survivors:
            print("   -> 🚨 种群全军覆没！环境过于恶劣。")
            return
            
        top_performers = survivors[:5] # 取前 5 名 Alpha
        
        print("\n   🏆 [Alpha Genes] 本世代存活下来的最强基因:")
        for rank, agent in enumerate(top_performers):
            print(f"      #{rank+1} {agent.agent_id} | 资金: ${agent.balance:.2f} | Risk: {agent.risk_tolerance:.1%} | Min EV: {agent.min_ev:.1%}")
            
        # 3. 基因交配与繁衍 (Crossover & Mutation)
        print("\n   -> 👩‍❤️‍👨 [Reproduction] 提取最强 Agent 的基因，开始繁衍下一代 (Generation 2)...")
        parent_a = top_performers[0]
        parent_b = top_performers[1]
        
        # 将最优基因写入系统灵魂
        soul_config = {
            "risk_tolerance": round(parent_a.risk_tolerance, 3),
            "min_ev": round(parent_a.min_ev, 3),
            "evolution_timestamp": time.time()
        }
        with open("standalone_workspace/core/agentic_os/soul_config.json", "w") as f:
            json.dump(soul_config, f, indent=2)
            
        print(f"   -> 💾 [Gene Imprint] 最强变异体的风控基因已写入主脑，系统完成自我迭代！")

if __name__ == "__main__":
    engine = SwarmEvolutionEngine(population_size=100)
    engine.run_evolution_epoch()
