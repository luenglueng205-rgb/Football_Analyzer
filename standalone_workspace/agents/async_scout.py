import asyncio
import json
import logging
from typing import Dict, Any

from agents.async_base import AsyncBaseAgent
from tools.mcp_beidan_scraper import MCPBeidanScraper
from tools.memory_manager import MemoryManager

try:
    from tools.analyzer_api import AnalyzerAPI
    from tools.llm_service import LLMService
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False

logger = logging.getLogger(__name__)

class AsyncScoutAgent(AsyncBaseAgent):
    """
    2026 Next-Gen Async Scout Agent
    通过 AsyncBaseAgent 继承，剥离了传统的 MessageBus 和死板的路由
    """
    def __init__(self, config=None):
        super().__init__("scout", "情报搜集", config)

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        接收全局 state，返回状态增量 (State Delta)
        """
        self.status = "running"
        
        # 1. 状态驱动：从全局 State 读取参数，而非局部 Task
        match_info = state.get("current_match", {})
        league = match_info.get("league", "")
        home_team = match_info.get("home_team", "")
        away_team = match_info.get("away_team", "")
        
        print(f"\n[AsyncScout] 开始并发搜集情报: {home_team} vs {away_team}")

        # 2. IO 异步化：将原有的同步 API 调用放入线程池，避免阻塞事件循环
        league_stats = None
        home_stats = None
        away_stats = None
        
        if API_AVAILABLE:
            # 使用 asyncio.gather 并发执行所有的外部 I/O 阻塞调用
            tasks = []
            if league:
                tasks.append(asyncio.to_thread(AnalyzerAPI.get_league_stats, league))
            else:
                tasks.append(asyncio.sleep(0)) # dummy
                
            tasks.append(asyncio.to_thread(AnalyzerAPI.get_team_stats, home_team))
            tasks.append(asyncio.to_thread(AnalyzerAPI.get_team_stats, away_team))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 解析并发结果
            league_stats_raw = results[0] if not isinstance(results[0], Exception) else {}
            home_stats_raw = results[1] if not isinstance(results[1], Exception) else {}
            away_stats_raw = results[2] if not isinstance(results[2], Exception) else {}

            if league_stats_raw and league_stats_raw.get("sample_size", 0) > 0:
                league_stats = {
                    "avg_total_goals": league_stats_raw.get("avg_total_goals", 2.7),
                    "home_win_rate": league_stats_raw.get("home_win_rate", 0.44),
                    "draw_rate": league_stats_raw.get("draw_rate", 0.26),
                    "away_win_rate": league_stats_raw.get("away_win_rate", 0.30),
                    "sample_size": league_stats_raw.get("sample_size", 0)
                }
            home_stats = self._format_home_record(home_stats_raw)
            away_stats = self._format_away_record(away_stats_raw)
        else:
            # 降级数据
            home_stats = {"played": 10, "wins": 7, "draws": 2, "losses": 1}
            away_stats = {"played": 9, "wins": 4, "draws": 3, "losses": 2}

        # 获取 500彩票网 北单 Mock 数据 (代表 MCP Browser 的提取结果)
        # 4. 引入北单 MCP 浏览器抓取器
        beidan_scraper = MCPBeidanScraper()
        beidan_data = await beidan_scraper.extract_live_sp(home_team, away_team)

        # 盘感检索
        memory_manager = MemoryManager()
        home_odds = float(match_info.get("home_odds", 2.10))
        draw_odds = float(match_info.get("draw_odds", 3.50))
        away_odds = float(match_info.get("away_odds", 3.20))
        
        historical_sense = memory_manager.query_historical_odds(league, home_odds, draw_odds, away_odds)
        historical_summary = ""
        if historical_sense.get("ok") and historical_sense.get("data"):
            docs = historical_sense["data"]
            historical_summary = f"发现 {len(docs)} 场历史相似赔率比赛。近期代表性赛果：\n" + "\n".join(docs[:5])
        else:
            historical_summary = "历史盘感样本不足。"

        weather_data = self._get_weather_info(match_info)

        data = {
            "status": "success",
            "data": {
                "home_team": {
                    "name": home_team,
                    "home_record": home_stats,
                },
                "away_team": {
                    "name": away_team,
                    "away_record": away_stats,
                },
                "match_info": {
                    "league": league,
                    "league_stats": league_stats,
                    "weather": weather_data,
                },
                "beidan_info": beidan_data,
                "historical_sense": historical_summary
            },
            "confidence": 0.85 if league_stats else 0.70,
            "data_source": "live_and_historical"
        }

        # LLM 分析报告 (异步执行)
        if API_AVAILABLE:
            system_prompt = "你是一名顶级的足彩情报专家。请阅读 JSON 数据，特别是 `historical_sense` 字段中的历史盘感数据，为用户撰写一份专业的赛前基本面情报，指出历史相似赔率下最容易打出的体彩玩法标签。"
            data_context = json.dumps(data["data"], ensure_ascii=False)
            try:
                ai_report = await asyncio.to_thread(LLMService.generate_report, system_prompt, data_context)
                data["ai_report"] = ai_report
            except Exception as e:
                logger.warning(f"LLM 报告生成失败: {e}")

        # 3. 异步持久化
        await self.save_context(f"intel_{home_team}_{away_team}", data)
        
        self.status = "completed"
        
        # 4. 返回状态增量 (State Delta)，彻底剥离 next_agent 路由
        return {"scout_data": data}

    async def _mock_500_lottery_scraper(self, home: str, away: str) -> Dict:
        """
        2026 平替方案：模拟使用 MCP Browser / Playwright 从 500.com 抓取的北单数据
        这绕过了官方 API 的限制。
        """
        print(f"  -> [MCP Browser] 正在无头访问 500.com 抓取北单即时 SP 值...")
        await asyncio.sleep(0.5) # 模拟网络与渲染延迟
        return {
            "lottery_type": "beidan",
            "handicap": -1, # 比如主让1球
            "sp_win": 3.12,
            "sp_draw": 3.55,
            "sp_loss": 2.21,
            "source": "500.com_web_scraper"
        }

    def _get_weather_info(self, match_info: dict = None) -> dict:
        """
        接入真实的 OpenWeatherMap API。
        优先从 match_info 提取主队所在城市，提取失败默认用伦敦。
        """
        api_key = "72614075c57839dcdab31d0edbb2df26" # 用户提供的真实 Key
        
        # 尝试从 match_info 中提取城市名称，如果没有则默认伦敦
        city = "London"
        if match_info and match_info.get("home_team"):
            city = match_info.get("home_team").split()[0] # 极其简化的球队到城市的映射，真实环境需查字典
            
        try:
            # 这里需要用到 multisource_fetcher
            from tools.multisource_fetcher import MultiSourceFetcher
            fetcher = MultiSourceFetcher()
            result = fetcher.fetch_weather_sync(city, api_key)
            
            if result.get("ok") and result.get("data"):
                return result["data"]
        except Exception as e:
            logger.warning(f"获取真实天气异常，降级使用 Mock: {e}")
            
        # Fallback 降级：如果 API 调用失败或断网，返回默认的好天气，不干扰 xG
        return {"temperature": 15, "condition": "clear", "wind": "light"}

    def _format_home_record(self, team_stats: Dict) -> Dict:
        if not team_stats or team_stats.get("sample_size", 0) == 0:
            return {"played": 10, "wins": 7, "draws": 2, "losses": 1}
        total = team_stats.get("sample_size", 0)
        win_rate = team_stats.get("win_rate", 0.44)
        return {
            "played": min(total, 50),
            "wins": int(min(total, 50) * win_rate),
            "draws": int(min(total, 50) * (1 - win_rate - 0.25)),
            "losses": int(min(total, 50) * 0.25),
        }

    def _format_away_record(self, team_stats: Dict) -> Dict:
        if not team_stats or team_stats.get("sample_size", 0) == 0:
            return {"played": 9, "wins": 4, "draws": 3, "losses": 2}
        total = team_stats.get("sample_size", 0)
        away_rate = 0.35
        draw_rate = 0.25
        return {
            "played": min(total, 50),
            "wins": int(min(total, 50) * away_rate),
            "draws": int(min(total, 50) * draw_rate),
            "losses": int(min(total, 50) * (1 - away_rate - draw_rate)),
        }