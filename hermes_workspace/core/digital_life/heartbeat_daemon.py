import asyncio
import json
import os
import sys
import time
import signal
import logging
import random
from datetime import datetime
from dotenv import load_dotenv

# 确保能加载 core_system
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from langchain_core.messages import SystemMessage, HumanMessage
from hermes_workspace.core.agentic_os.state_graph_orchestrator import compile_agentic_graph
from hermes_workspace.core.agentic_os.hippocampus import HippocampusMemory
from hermes_workspace.agents.auto_tuner_agent import AutoTunerAgent

# 配置生命体日志系统 (输出到归档目录，防止污染)
LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../core_system/artifacts/reports/daemon_heartbeat.log"))
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DigitalLifeDaemon")

class DigitalLifeDaemon:
    """
    2026 AI-Native: 永生心跳引擎 (Continuous Autonomy Daemon)
    赋予系统 7x24 小时的自主生命权。它会像呼吸一样定期感知外部世界，
    一旦发现猎物（赔率异动、新开盘），就会唤醒 LangGraph 状态机进行猎杀。
    """
    def __init__(self, interval_seconds=300):
        self.interval_seconds = interval_seconds
        self.is_alive = False
        self.brain_app = compile_agentic_graph()
        self.hippo = HippocampusMemory()
        self.auto_tuner = AutoTunerAgent()
        self.last_consolidation_date = None
        
        # 注册平滑退出信号
        signal.signal(signal.SIGINT, self._graceful_shutdown)
        signal.signal(signal.SIGTERM, self._graceful_shutdown)
        
        load_dotenv()
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("⚠️ 未检测到大模型 API_KEY，守护进程将在盲态下运行。")

    def _graceful_shutdown(self, signum, frame):
        logger.info("\n🧬 [Shutdown] 收到终止信号，正在休眠数字生命中枢... 晚安。")
        self.is_alive = False
        sys.exit(0)

    def _perceive_environment(self):
        """
        感知器官：主动去外部世界嗅探信息。
        (实盘中这里会调用如 API-Football 或 500彩票网的轮询接口)
        """
        logger.info("   -> 👁️ [Perception] 正在扫描全球实时盘口与基本面数据...")
        
        # 模拟：有 30% 的概率发现高价值猎物
        if random.random() < 0.3:
            logger.info("   -> 🚨 [Alert] 嗅探到赔率剧烈波动！发现高价值猎物！")
            return {
                "match_id": f"LIVE_{int(time.time())}",
                "context": "英超: 曼联 vs 热刺。情报: 热刺核心中场赛前突发高烧无法出战，曼联主场以逸待劳。",
                "odds": 1.95,
                "xg": {"home": 1.7, "away": 0.8}
            }
        else:
            logger.info("   -> 💤 [Perception] 当前市场如死水般平静，继续潜伏。")
            return None

    def _awaken_agents(self, prey_data):
        """
        神经突触：一旦发现猎物，瞬间唤醒大模型图结构 (StateGraph)
        """
        logger.info(f"   -> 🧠 [Awaken] 正在唤醒沉睡的 AI 专家处理赛事: {prey_data['context']}")
        
        initial_state = {
            "messages": [
                SystemMessage(content="你是专注英超的激进派量化分析师。执行SOP：1. 计算真实概率。2. 过风控。3. 必须调用 check_balance 查询资金。4. 根据资金按10%仓位调用 execute_ticket_route 路由出票。"),
                HumanMessage(content=f"新情报：{prey_data['context']}。主胜赔率 {prey_data['odds']}。主队预期进球 {prey_data['xg']['home']}，客队 {prey_data['xg']['away']}。")
            ],
            "match_context": prey_data["context"],
            "official_odds": prey_data["odds"],
            "risk_status": "PENDING",
            "true_probs": {}
        }
        
        try:
            for output in self.brain_app.stream(initial_state, {"recursion_limit": 30}):
                pass
            logger.info("   -> ✅ [Execution] 猎杀完成，大脑重新进入休眠状态。")
            
            # 【记忆写入】: 将本次交易记入海马体日记本
            # 备注：实盘中真实盈亏需要在赛后获取，此处先写入预测环境的快照
            self.hippo.record_episode(
                match_id=prey_data["match_id"],
                action="ANALYZE", 
                pnl=0, 
                context_snapshot={"league": "英超", "odds": prey_data["odds"]}
            )
            
        except Exception as e:
            logger.error(f"   -> ❌ [Error] 神经元短路，处理失败: {e}")

    def start(self, test_mode=False):
        """启动生命心跳"""
        self.is_alive = True
        logger.info("==================================================")
        logger.info("🩸 [Heartbeat Engine] 永生守护进程已启动！")
        logger.info(f"⏱️ 呼吸频率: 每 {self.interval_seconds} 秒扫描一次全球盘口。")
        logger.info("==================================================")

        loops = 0
        while self.is_alive:
            now = datetime.now()
            logger.info(f"💓 [Pulse] 心跳正常... (当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')})")
            
            # 【夜间生物钟】: 每天凌晨 3 点，海马体进行深度休眠与记忆重塑
            if now.hour == 3 and self.last_consolidation_date != now.date():
                logger.info("   -> 🌙 [Circadian Rhythm] 触发夜间生物钟，开始反思今日得失...")
                self.hippo.sleep_and_consolidate()
                
                # === 🚀 集成 Agentic Auto-Tuning 进化循环 ===
                logger.info("   -> 🧬 [Auto-Tuner] 唤醒进化军师，开始深度复盘与超参数迭代...")
                try:
                    # 从海马体读取昨日的情节记录 (episodic.json)
                    with open(self.hippo.episodic_memory_file, "r", encoding="utf-8") as f:
                        episodes = json.load(f)
                    
                    if not episodes:
                        logger.info("   -> ⚠️ [Auto-Tuner] 昨夜无交易记录，跳过进化循环。")
                    else:
                        # 组装军师所需的 pnl_report 战报格式
                        total = len(episodes)
                        wins = len([e for e in episodes if e.get("PnL", 0) > 0])
                        total_profit = sum(e.get("PnL", 0) for e in episodes)
                        
                        pnl_report = {
                            "total_simulated": total,
                            "win_rate": wins / total if total > 0 else 0.0,
                            "roi": total_profit / total if total > 0 else 0.0,
                            "total_profit": total_profit,
                            "details": [
                                {
                                    "status": "LOSS" if e.get("PnL", 0) < 0 else "WIN",
                                    "odds": [e.get("context", {}).get("odds", 2.0)],
                                    **e
                                } for e in episodes
                            ]
                        }
                        
                        # 触发军师进行进化闭环，重写 hyperparams.json 和 DYNAMIC_EXPERIENCE.md
                        evolution_result = asyncio.run(self.auto_tuner.run_evolution_cycle(pnl_report))
                        
                        if evolution_result and evolution_result.get("ok"):
                            logger.info("   -> ✅ [Evolution] 进化完成！系统基因(超参数)已成功更新。")
                except Exception as e:
                    logger.error(f"   -> ❌ [Evolution Error] 进化反思失败: {e}")
                # ===============================================
                
                self.last_consolidation_date = now.date()

            # 1. 感知外部世界
            prey = self._perceive_environment()
            
            # 2. 如果发现猎物，则唤醒大脑处理
            if prey:
                self._awaken_agents(prey)
                
            # 测试模式下只跳动一次就退出
            if test_mode:
                logger.info("🛠️ [Test Mode] 测试完成，自动结束心跳。")
                break
                
            # 3. 休眠，等待下一次心跳
            time.sleep(self.interval_seconds)

if __name__ == "__main__":
    # 如果带 --test 参数则只运行一次
    test_mode = "--test" in sys.argv
    # 生产环境建议 15分钟(900秒) 扫一次盘，测试用 3秒
    interval = 3 if test_mode else 900
    
    daemon = DigitalLifeDaemon(interval_seconds=interval)
    daemon.start(test_mode=test_mode)
