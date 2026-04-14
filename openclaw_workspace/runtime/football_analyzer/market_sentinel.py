import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
from agents.syndicate_os import SyndicateOS
from tools.analyzer_api import AnalyzerAPI
from tools.pre_filter import MatchPreFilter
from agents.publisher_agent import PublisherAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MarketSentinel:
    def __init__(self, max_workers: int = 3):
        self.os_system = SyndicateOS()
        self.publisher = PublisherAgent()
        self.pre_filter = MatchPreFilter()
        self.polling_interval = 3600
        self.analyzed_matches = set()
        
        # 协程池参数
        self.max_workers = max_workers
        self.queue = asyncio.Queue()

    async def _worker(self, worker_id: int, published_reports: Optional[List[str]] = None):
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
                if published_reports is not None:
                    date_str = datetime.now().strftime("%Y%m%d")
                    published_reports.append(self.publisher.report_path(home, away, date_str))
                
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

    async def run_once(self) -> Dict:
        published_reports: List[str] = []
        workers = [asyncio.create_task(self._worker(i, published_reports)) for i in range(self.max_workers)]
        analyzed_before = len(self.analyzed_matches)

        try:
            opportunities = await self._fetch_market_scan()

            enqueued = 0
            skipped = 0
            for opp in opportunities:
                match_key = f"{opp.get('home_team')}_vs_{opp.get('away_team')}"
                if match_key not in self.analyzed_matches:
                    await self.queue.put(opp)
                    enqueued += 1
                else:
                    skipped += 1

            if not self.queue.empty():
                await self.queue.join()

            analyzed_after = len(self.analyzed_matches)
            return {
                "fetched": len(opportunities),
                "enqueued": enqueued,
                "skipped": skipped,
                "newly_analyzed": analyzed_after - analyzed_before,
                "analyzed_total": analyzed_after,
                "publisher_report_paths": published_reports,
            }
        finally:
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

    async def run_forever(self):
        logging.info("==================================================")
        logging.info("🛡️ 7x24 Market Sentinel (Worker Pool Edition)")
        logging.info("==================================================")
        
        # 启动消费者协程池
        workers = [asyncio.create_task(self._worker(i)) for i in range(self.max_workers)]

        try:
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
        finally:
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

if __name__ == "__main__":
    sentinel = MarketSentinel()
    try:
        asyncio.run(sentinel.run_forever())
    except KeyboardInterrupt:
        print("\nSentinel stopped by user.")
