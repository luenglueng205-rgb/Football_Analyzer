import asyncio
import logging
from typing import List, Dict
from agents.syndicate_os import SyndicateOS
from tools.analyzer_api import AnalyzerAPI
from tools.pre_filter import MatchPreFilter
from agents.publisher_agent import PublisherAgent
from tools.pre_match_sentinel import PreMatchSentinel
from tools.live_match_monitor import LiveMatchMonitor
from tools.settlement_engine import SettlementEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MarketSentinel:
    def __init__(self, max_workers: int = 3):
        self.os_system = SyndicateOS()
        self.publisher = PublisherAgent()
        self.pre_filter = MatchPreFilter()
        
        # Lifecycle Managers
        self.pre_match_sentinel = PreMatchSentinel()
        self.live_monitor = LiveMatchMonitor()
        self.settlement_engine = SettlementEngine()
        
        self.polling_interval = 3600
        self.analyzed_matches = set()
        
        # Worker Pool
        self.max_workers = max_workers
        self.queue = asyncio.Queue()

    async def _worker(self, worker_id: int):
        """消费者协程：从队列中取比赛进行深度分析"""
        logging.info(f"[Worker-{worker_id}] 启动，等待任务...")
        while True:
            match = await self.queue.get()
            home = match.get('home_team')
            away = match.get('away_team')
            match_key = f"{home}_vs_{away}"
            
            try:
                logging.info(f"[Worker-{worker_id}] 🔴 开始深度分析: {match_key}")
                
                # 核心分析链路
                res = await self.os_system.process_match(home, away, "竞彩足球")
                
                # 自动生成研报
                await self.publisher.publish(home, away, res)
                
                # 记录已分析
                self.analyzed_matches.add(match_key)
                
                logging.info(f"[Worker-{worker_id}] 🟢 完成分析: {match_key}")
                
                # 防封禁缓冲：分析完一场休息 10 秒
                await asyncio.sleep(10)
                
            except Exception as e:
                logging.error(f"[Worker-{worker_id}] 分析 {match_key} 异常: {e}")
            finally:
                self.queue.task_done()

    async def _fetch_market_scan(self) -> List[Dict]:
        """生产者：获取市场赛程并经过初筛漏斗"""
        logging.info("[Sentinel] 获取今日实单赛程...")
        fixtures = AnalyzerAPI.get_live_fixtures()
        
        upcoming = [f for f in fixtures if f.get("status") == "upcoming"]
        logging.info(f"[Sentinel] 发现 {len(upcoming)} 场未开赛。进入初筛漏斗...")
        
        # 初筛漏斗
        valuable_matches = self.pre_filter.filter_matches(upcoming)
        logging.info(f"[Sentinel] 初筛后剩余 {len(valuable_matches)} 场高价值比赛。")
        
        return valuable_matches

    async def _pre_match_loop(self):
        """T-30 Lineup Monitor: Checks if key players are actually starting."""
        logging.info("[Lifecycle] Pre-Match Sentinel loop started.")
        while True:
            try:
                for match_id, info in list(self.pre_match_sentinel.monitored_matches.items()):
                    if info["status"] == "monitored":
                        # Mocking actual starting XI API call
                        actual_xi = info["key_players"][:-1] if len(info["key_players"]) > 1 else [] # Simulate a missing player occasionally
                        res = self.pre_match_sentinel.check_lineups_t30(match_id, actual_xi)
                        if res.get("recommended_action") == "CANCEL_BET":
                            logging.error(f"[Lifecycle] 🚨 CANCEL BET for {match_id}. EV dropped to {res['adjusted_ev']}")
                            info["status"] = "cancelled"
                        elif res.get("recommended_action") == "PROCEED":
                            info["status"] = "confirmed"
            except Exception as e:
                logging.error(f"[Lifecycle] Pre-match loop error: {e}")
            await asyncio.sleep(600) # Check every 10 mins

    async def _in_play_loop(self):
        """Live Hedging Monitor: Evaluates live odds for cash-out/hedge opportunities."""
        logging.info("[Lifecycle] In-Play Monitor loop started.")
        while True:
            try:
                for match_id, bet in list(self.live_monitor.active_bets.items()):
                    if bet["status"] == "active":
                        # Mocking live data (75th minute, 1-0, odds against: 4.5)
                        res = self.live_monitor.evaluate_hedge_opportunity(match_id, "1-0", 4.5, 76)
                        if res.get("recommended_action") == "HEDGE_NOW":
                            logging.warning(f"[Lifecycle] 🚨 EXECUTING HEDGE for {match_id}. Guaranteed Profit: {res['guaranteed_profit']}")
                            bet["status"] = "hedged"
            except Exception as e:
                logging.error(f"[Lifecycle] In-play loop error: {e}")
            await asyncio.sleep(300) # Check every 5 mins

    async def _post_match_loop(self):
        """Strict Settlement Engine: Settles bets according to official rules."""
        logging.info("[Lifecycle] Post-Match Settlement loop started.")
        while True:
            try:
                # Mock fetching finished match results
                finished_matches = {
                    "MOCK_MATCH_1": {"status": "SETTLED", "official_result": "3", "ft_score": "2-1", "odds_applied": "market_odds"}
                }
                # Normally, we would iterate over unsettled tickets in the ledger
                pass
            except Exception as e:
                logging.error(f"[Lifecycle] Settlement loop error: {e}")
            await asyncio.sleep(3600) # Check hourly

    async def run_forever(self):
        logging.info("==================================================")
        logging.info("🛡️ 7x24 Market Sentinel (Lifecycle Mastery Edition)")
        logging.info("==================================================")
        
        # 启动生命周期监控协程
        asyncio.create_task(self._pre_match_loop())
        asyncio.create_task(self._in_play_loop())
        asyncio.create_task(self._post_match_loop())
        
        # 启动消费者协程池
        workers = [asyncio.create_task(self._worker(i)) for i in range(self.max_workers)]
        
        while True:
            try:
                opportunities = await self._fetch_market_scan()
                
                # 投递任务
                for opp in opportunities:
                    match_key = f"{opp.get('home_team')}_vs_{opp.get('away_team')}"
                    if match_key not in self.analyzed_matches:
                        await self.queue.put(opp)
                        
                # 等待队列中的任务全部完成
                if not self.queue.empty():
                    logging.info(f"[Sentinel] 投递了 {self.queue.qsize()} 个新任务到池中，等待处理...")
                    await self.queue.join()
                    logging.info("[Sentinel] 本轮洪峰任务处理完毕。")
                else:
                    logging.info("[Sentinel] 当前无新任务。")
                    
                logging.info(f"💤 Sentinel 睡眠 {self.polling_interval} 秒...")
                await asyncio.sleep(self.polling_interval)
                
            except Exception as e:
                logging.error(f"Sentinel 遭遇错误: {e}")
                await asyncio.sleep(300)

if __name__ == "__main__":
    sentinel = MarketSentinel()
    try:
        asyncio.run(sentinel.run_forever())
    except KeyboardInterrupt:
        print("\nSentinel stopped by user.")
