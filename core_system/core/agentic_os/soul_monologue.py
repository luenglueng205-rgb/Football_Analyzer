import asyncio
import signal
import random
import logging
from datetime import datetime
from pathlib import Path

try:
    from .hippocampus import HippocampusMemory
    from .evolution_engine import EvolutionEngine
except ImportError:
    from hippocampus import HippocampusMemory
    from evolution_engine import EvolutionEngine


_AGENTIC_OS_DIR = Path(__file__).resolve().parent
_CORE_SYSTEM_ROOT = _AGENTIC_OS_DIR.parents[1]
_DEFAULT_MEMORY_DIR = _CORE_SYSTEM_ROOT / "workspace" / "orchestrator" / "memory_core"
_DEFAULT_SOUL_CONFIG_PATH = _AGENTIC_OS_DIR / "soul_config.json"

logger = logging.getLogger(__name__)

class AgenticSoul:
    """
    2026 Agentic OS - 核心灵魂 (Continuous Inner Monologue)
    这是一个死循环。它让 Agent 拥有了“待机时的意识流”和自我调度的权力。
    """
    def __init__(self, memory_dir=None, config_file=None):
        self.memory_dir = Path(memory_dir).expanduser() if memory_dir else _DEFAULT_MEMORY_DIR
        self.config_file = Path(config_file).expanduser() if config_file else _DEFAULT_SOUL_CONFIG_PATH
        self.semantic_file = self.memory_dir / "semantic_truth.json"

        self.hippo = HippocampusMemory(memory_dir=str(self.memory_dir))
        self.evo = self._build_evolution_engine()
        self.is_alive = True
        self.tick_count = 0
        self._loop = None  # 保存事件循环引用，供信号处理使用

    def _build_evolution_engine(self):
        # EvolutionEngine.__init__ 仍然内置旧路径，直接接管构造流程以避免回写历史布局。
        evo = EvolutionEngine.__new__(EvolutionEngine)
        evo.semantic_file = str(self.semantic_file)
        evo.config_file = str(self.config_file)
        evo._init_config()
        return evo

    async def _think(self, thought):
        """模拟内心独白的思考延迟"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 💭 [Inner Monologue]: {thought}")
        await asyncio.sleep(random.uniform(1.0, 3.0))

    async def conscious_loop(self):
        """意识流主循环。is_alive 完全由外部控制（信号、业务逻辑等）。"""
        print("==================================================")
        print("🌌 [Agentic OS] 注入系统灵魂，意识流循环已启动...")
        print("==================================================")

        # 注册信号处理器（Python 3.8+ loop.add_signal_handler，仅在 Unix 可用）
        self._loop = asyncio.get_running_loop()
        self._register_signal_handlers()

        try:
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

                await asyncio.sleep(2)  # 模拟呼吸频率
        finally:
            logger.info("[Soul] 意识流循环已停止，执行优雅停机 (tick_count=%d)", self.tick_count)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌙 [Soul] 优雅停机完成，共完成 {self.tick_count} 次心跳。")

    def _register_signal_handlers(self):
        """在事件循环上注册 SIGTERM/SIGINT 信号处理器。

        策略：
        1. 优先使用 loop.add_signal_handler（Python 3.8+，仅在 Unix 可用）
           - 回调运行在事件循环线程中，可直接通过闭包修改 self.is_alive
        2. Windows 不支持 add_signal_handler 时，回退到 signal.signal
           - signal.signal 要求回调是普通函数（C 签名限制），不能是实例方法
           - 利用闭包默认参数捕获 self 引用来绕过此限制
        3. 某些受限环境（子进程、测试）无法注册任何信号处理器时静默跳过
        """
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                # 路径 A: loop.add_signal_handler — 闭包直接捕获 self
                soul_ref = self
                def _handler(signum, _ref=soul_ref):
                    _ref.is_alive = False
                    logger.info("[Soul] 收到信号 %s，准备优雅停机", signum)
                self._loop.add_signal_handler(sig, _handler)
                logger.debug("[Soul] 已注册信号处理器 (loop): %s", sig.name)
            except (NotImplementedError, OSError, ValueError):
                # 路径 B: signal.signal 回退（Windows / 事件循环未就绪）
                try:
                    soul_ref = self
                    def _fallback(signum, frame, _ref=soul_ref):
                        _ref.is_alive = False
                        logger.info("[Soul] 收到信号 %s，准备优雅停机", signum)
                    signal.signal(sig, _fallback)
                    logger.debug("[Soul] 已注册信号处理器 (signal): %s", sig.name)
                except (ValueError, OSError):
                    logger.debug("[Soul] 无法注册信号处理器 %s，跳过", sig.name)

if __name__ == "__main__":
    soul = AgenticSoul()
    asyncio.run(soul.conscious_loop())
