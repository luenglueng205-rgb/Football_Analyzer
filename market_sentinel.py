import asyncio
import time
import logging
from agents.syndicate_os import SyndicateOS
from tools.analyzer_api import AnalyzerAPI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MarketSentinel:
    """
    P4 阶段：7x24 自动化市场监控与决策引擎 (Daemon)
    真实拉取 500.com 赛程，循环驱动大模型分析。
    """
    def __init__(self):
        self.agent = SyndicateOS()
        self.polling_interval = 3600  # 1小时扫描一次全市场
        self.analyzed_matches = set() # 记录已分析过的比赛，避免重复推送
        
    async def _fetch_market_scan(self):
        """真实调用底层能力获取今日赛程，寻找机会"""
        logging.info("[Sentinel] 正在连接数据织机获取今日实单赛程...")
        fixtures = AnalyzerAPI.get_live_fixtures()
        
        upcoming_matches = [f for f in fixtures if f.get("status") == "upcoming"]
        logging.info(f"[Sentinel] 今日共发现 {len(fixtures)} 场比赛，其中未开赛 {len(upcoming_matches)} 场。")
        
        return upcoming_matches

    async def run_forever(self):
        logging.info("==================================================")
        logging.info("🛡️ 7x24 Market Sentinel Daemon Started (P4 Edition)")
        logging.info("==================================================")
        
        while True:
            try:
                opportunities = await self._fetch_market_scan()
                
                for opp in opportunities:
                    home = opp.get('home_team')
                    away = opp.get('away_team')
                    match_key = f"{home}_vs_{away}"
                    
                    if match_key in self.analyzed_matches:
                        continue # 已分析过
                        
                    logging.warning(f"🚨 [ALERT] 发现新赛事机会: {home} vs {away}")
                    
                    state = {
                        "current_match": {
                            "home_team": home,
                            "away_team": away
                        },
                        "params": {
                            "lottery_type": "jingcai",
                            "lottery_desc": "竞彩足球 (单场/串关)"
                        }
                    }
                    
                    # 唤醒大模型进行深度决策
                    logging.info(f"🧠 Waking up SyndicateOS for {match_key}...")
                    result = await self.agent.process_match(home, away, state["params"]["lottery_desc"])
                    
                    # 分析完毕，加入已分析集合
                    self.analyzed_matches.add(match_key)
                    
                    decision = result.get("final_decision", "")
                    if "✅ 投注成功" in decision or "execute_bet" in decision or "ev" in decision.lower():
                        logging.info(f"✅ AI 发现可投资机会！推送通知...")
                        # 此时其实内部的大模型已经调用了 send_webhook_notification 和 generate_qr_code
                    else:
                        logging.info(f"⚠️ AI 放弃了 {match_key} (风控拦截)。")
                    
                    # 避免对 API 和模型造成太大压力，每场比赛分析间隔 1 分钟
                    await asyncio.sleep(60)
                    
                logging.info(f"💤 Sentinel 本轮巡航结束，睡眠 {self.polling_interval} 秒...")
                await asyncio.sleep(self.polling_interval)
                
            except Exception as e:
                logging.error(f"Sentinel encountered an error: {e}")
                await asyncio.sleep(300) # 出错时休眠5分钟再试

if __name__ == "__main__":
    sentinel = MarketSentinel()
    try:
        asyncio.run(sentinel.run_forever())
    except KeyboardInterrupt:
        print("\nSentinel stopped by user.")
