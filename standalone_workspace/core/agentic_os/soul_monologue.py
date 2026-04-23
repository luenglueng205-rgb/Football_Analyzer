import asyncio
import time
import random
from datetime import datetime

# 模拟导入刚刚写好的记忆体和进化引擎
from standalone_workspace.core.agentic_os.hippocampus import HippocampusMemory
from standalone_workspace.core.agentic_os.evolution_engine import EvolutionEngine

class AgenticSoul:
    """
    2026 Agentic OS - 核心灵魂 (Continuous Inner Monologue)
    这是一个死循环。它让 Agent 拥有了“待机时的意识流”和自我调度的权力。
    """
    def __init__(self):
        self.hippo = HippocampusMemory()
        self.evo = EvolutionEngine()
        self.is_alive = True
        self.tick_count = 0

    async def _think(self, thought):
        """模拟内心独白的思考延迟"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 💭 [Inner Monologue]: {thought}")
        await asyncio.sleep(random.uniform(1.0, 3.0))

    async def conscious_loop(self):
        print("==================================================")
        print("🌌 [Agentic OS] 注入系统灵魂，意识流循环已启动...")
        print("==================================================")
        
        while self.is_alive:
            self.tick_count += 1
            hour = datetime.now().hour
            
            # 1. 状态自检与闲聊 (Idle Monologue)
            if self.tick_count % 3 == 0:
                await self._think("又是新的一天，昨天的战绩如何？我得去看看海马体的情节日记...")
            
            # 2. 触发记忆重塑与自我进化 (Memory Consolidation)
            if self.tick_count % 4 == 0:
                await self._think("我好像连续在同一个盘口上吃亏了，我需要启动深度休眠，提炼一下规则。")
                self.hippo.sleep_and_consolidate()
                await self._think("规则提炼完成。现在我将调用进化引擎，进行系统配置的热更新（自我手术）。")
                self.evo.trigger_evolution()
                
            # 3. 主动寻猎 (Active Hunting)
            if hour >= 14 and hour <= 23:
                await self._think("比赛高峰期到了。即使主人没有下达指令，我也必须主动唤醒 Rust 边缘节点去扫盘。")
                # 模拟唤醒中层的大脑
                print("   -> 📡 [Soul] 发送系统级唤醒指令 -> [Cloud Brain] & [Edge Limbs]...")
                await asyncio.sleep(1)
            else:
                await self._think("现在是凌晨。盘口很安静。我可以花点算力去运行 MCTS 在脑海里下棋，测试一下极端行情...")
                
            # 4. 环境感知 (Environment Sensing)
            # 模拟随机接收到一个外部突发事件
            if random.random() > 0.8:
                await self._think("等等！我刚才似乎捕捉到威廉希尔的 API 报了一个 403 错误。我要把它记下来，也许是他们反爬策略升级了。")
            
            await asyncio.sleep(2) # 模拟呼吸频率
            
            if self.tick_count >= 6: # 演示用，执行 6 次心跳后退出
                await self._think("系统维护指令收到。准备进行意识剥离，进入关机状态...")
                self.is_alive = False

if __name__ == "__main__":
    soul = AgenticSoul()
    asyncio.run(soul.conscious_loop())
