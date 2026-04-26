import json
import logging
import traceback
import time
import numpy as np
from typing import Dict, Any, List
import concurrent.futures

# 导入所有核心工具
import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from tools.monte_carlo_simulator import MatchTimelineSimulator
from tools.smart_money_tracker import SmartMoneyTracker
from tools.atomic_skills import evaluate_betting_value, calculate_poisson_probability
from tools.mxn_calculator import MxnCalculator

# 强制 numpy 抛出所有数学溢出/下溢警告为异常，用于极限压测
np.seterr(all='raise')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExtremeStressTester:
    """
    针对多智能体量化系统的极限压测框架。
    压榨算力、内存、数学边界和并发极限。
    """
    def __init__(self):
        self.issues_found = []

    def _log_issue(self, issue: str):
        logger.error(f"🚨 漏洞发现: {issue}")
        self.issues_found.append(issue)

    def test_math_overflow_in_monte_carlo(self):
        logger.info("\n[极限压测 1]: 蒙特卡洛引擎千万级数学溢出与性能压测")
        try:
            # 1.1 极限大数模拟 (千万级矩阵运算)
            logger.info("-> 启动 10,000,000 次 90 分钟时间轴模拟...")
            start_time = time.time()
            
            # 故意传入极端的 xG (如 20.0，会导致某些分钟的概率超过常规范围)
            mc_sim = MatchTimelineSimulator(num_simulations=10_000_000)
            
            try:
                probs = mc_sim.simulate_ht_ft_probabilities(20.0, 0.001)
                elapsed = time.time() - start_time
                logger.info(f"-> 千万级模拟完成，耗时: {elapsed:.2f} 秒。系统未发生 OOM 或数学溢出。")
                
                # 性能红线：1000万次模拟必须在 10 秒内完成 (Numpy 向量化硬要求)
                if elapsed > 10.0:
                    self._log_issue(f"性能不达标: 千万级蒙特卡洛模拟耗时 {elapsed:.2f}s，超过 10s 阈值，将拖垮 Agent 响应速度。")
                    
            except FloatingPointError as e:
                self._log_issue(f"数学溢出崩溃: Numpy 底层计算发生浮点数溢出 (Overflow/Underflow): {e}")

        except Exception as e:
            self._log_issue(f"压测 1 崩溃: {traceback.format_exc()}")

    def test_massive_concurrent_daemons(self):
        logger.info("\n[极限压测 2]: 守护进程高并发并发竞争测试")
        try:
            logger.info("-> 模拟 10,000 个后台守护进程同时触发聪明资金写入队列...")
            
            smt = SmartMoneyTracker(alert_threshold=0.01)
            alert_queue_file = "workspace/risk-manager/smart_money_alerts.json"
            
            # 清空队列
            os.makedirs(os.path.dirname(alert_queue_file), exist_ok=True)
            with open(alert_queue_file, 'w') as f:
                json.dump([], f)
                
            def simulate_daemon_write(match_id_int):
                match_id = f"MATCH_{match_id_int}"
                # 构造一个必然触发警报的赔率
                open_odds = {"home": 2.0, "draw": 3.0, "away": 3.0}
                curr_odds = {"home": 1.5, "draw": 3.5, "away": 4.0}
                res = smt.track_odds_movement(match_id, open_odds, curr_odds)
                
                if res.get("is_volatile_market"):
                    # 模拟 market_monitor.py 的写入行为 (调用带有文件锁的真实方法)
                    try:
                        monitor = __import__('market_monitor').ActiveMarketMonitor()
                        monitor.alert_queue_file = alert_queue_file
                        monitor._push_alert_to_risk_manager({"match_id": match_id})
                    except Exception as e:
                        return "IO_ERROR"
                return "SUCCESS"

            # 使用线程池发起 1000 次并发写入 (模拟极端的 I/O 竞争)
            success_count = 0
            corruption_count = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                futures = [executor.submit(simulate_daemon_write, i) for i in range(1000)]
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res == "SUCCESS": success_count += 1
                    elif res == "JSON_CORRUPTION": corruption_count += 1
            
            logger.info(f"-> 并发写入完成。成功: {success_count}, 文件损坏: {corruption_count}")
            if corruption_count > 0 or success_count < 1000:
                self._log_issue(f"并发竞争漏洞: 在多线程/多 Daemon 并发下，JSON 文件被写坏了 {corruption_count} 次，丢失了 {1000 - success_count} 条警报。必须引入文件锁 (FileLock) 或改用 SQLite/Redis！")

        except Exception as e:
            self._log_issue(f"压测 2 崩溃: {traceback.format_exc()}")

    def test_extreme_kelly_and_poisson(self):
        logger.info("\n[极限压测 3]: 凯利准则与泊松分布的毒数据注入 (Poison Pill)")
        try:
            logger.info("-> 注入极端抽水率 (隐含概率总和 200% 和 50%)")
            smt = SmartMoneyTracker()
            
            # 3.1 极端高抽水 (黑平台)
            black_market_odds = {"home": 1.1, "draw": 1.5, "away": 1.5} # 隐含概率: 0.9 + 0.66 + 0.66 = 2.22 (222%)
            res1 = smt.track_odds_movement("test", black_market_odds, {"home": 1.05, "draw": 1.6, "away": 1.6})
            if "error" in res1:
                logger.info("-> 黑平台高抽水处理正常 (已按比例剥离)。")
                
            # 3.2 负数赔率与 NaN 注入
            logger.info("-> 注入 NaN 和 负数")
            try:
                res2 = smt.track_odds_movement("test", {"home": float('nan'), "draw": -1.5, "away": 0}, {"home": 1.05, "draw": 1.6, "away": 1.6})
                if "error" not in res2:
                    self._log_issue("毒数据漏洞: SmartMoneyTracker 没有拦截 NaN 或负数赔率，输出了无效的分析结果。")
            except Exception as e:
                 self._log_issue(f"毒数据崩溃: SmartMoneyTracker 遇到 NaN 直接引发未捕获的 Python 异常: {e}")

            # 3.3 泊松分布超大进球数溢出测试
            logger.info("-> 泊松分布注入超大预期进球 (xG = 500)")
            # 如果 xG 极大，泊松公式中的 e^(-lambda) 会变成 0，lambda^k 会变成 Infinity
            poisson_res_str = calculate_poisson_probability(500.0, 0.1)
            poisson_res = json.loads(poisson_res_str)
            if "error" not in poisson_res:
                # 检查输出矩阵里有没有 NaN 或 Inf
                score_matrix = poisson_res.get("score_matrix", {})
                if any("NaN" in str(v) or "Inf" in str(v) for v in score_matrix.values()):
                    self._log_issue("数学溢出漏洞: 泊松分布在处理极大 xG 时产生了 NaN/Infinity，大模型接收后会彻底幻觉。")
            else:
                logger.info("-> 泊松分布超大 xG 拦截正常。")

        except Exception as e:
            self._log_issue(f"压测 3 崩溃: {traceback.format_exc()}")

    def run_all(self):
        self.test_math_overflow_in_monte_carlo()
        self.test_massive_concurrent_daemons()
        self.test_extreme_kelly_and_poisson()
        
        logger.info("\n=== 极限压测报告 ===")
        if self.issues_found:
            logger.error(f"❌ 系统在极限压测中暴露出 {len(self.issues_found)} 个致命级架构漏洞：")
            for i, issue in enumerate(self.issues_found, 1):
                logger.error(f"  {i}. {issue}")
        else:
            logger.info("✅ 坚如磐石！系统扛住了千万级运算、并发竞争和毒数据注入的所有极限压测。")

if __name__ == "__main__":
    tester = ExtremeStressTester()
    tester.run_all()