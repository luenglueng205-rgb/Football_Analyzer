import time
import os
import threading
from typing import Dict, Any
import requests
import xml.etree.ElementTree as ET
import re

class SocialNewsListener:
    """
    毫秒级情报监听器 (核心逻辑) - ZSA 快轨真实环境版
    通过后台守护线程常驻内存，每隔 30 秒轮询真实的 RSS/Twitter 源。
    当外部通过 MCP 访问时，直接 O(1) 返回内存缓存，实现 0ms 延迟。
    """
    def __init__(self, use_mock: bool = None):
        # 优先读取环境变量，默认关闭 mock (进入实战模式)
        env_mock = os.getenv("NEWS_LISTENER_MOCK", "false").lower() in ("true", "1", "yes")
        self.use_mock = env_mock if use_mock is None else use_mock
        
        self.rss_feeds = [
            "https://feeds.bbci.co.uk/sport/football/rss.xml",
            "https://www.skysports.com/rss/12040"
        ]
        
        # 内存缓存，用于存储各个球队的最新情报和 xG 影响
        self._cache = {}
        self._cache_lock = threading.Lock()
        
        # 启动后台常驻轮询线程
        if not self.use_mock:
            self._polling_thread = threading.Thread(target=self._background_poll, daemon=True)
            self._polling_thread.start()
            print("   -> 🚀 [ZSA 快轨] SocialNewsListener 常驻内存守护线程已启动...")

    def _background_poll(self):
        """后台轮询线程：不断抓取 RSS/Twitter 存入缓存"""
        # 注意：在真实生产环境中，应通过 Twitter API 或 webhook 监听。此处以 RSS 轮询作为 Phase 1 骨架。
        while True:
            try:
                # 抓取所有源
                all_news = []
                for url in self.rss_feeds:
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        root = ET.fromstring(resp.content)
                        for item in root.findall('./channel/item'):
                            title = item.find('title').text or ""
                            desc = item.find('description').text or ""
                            all_news.append((title, desc))
                
                # 如果缓存中有正在被关注的球队，更新它们的情报
                with self._cache_lock:
                    watched_teams = list(self._cache.keys())
                
                for team in watched_teams:
                    team_news = []
                    for title, desc in all_news:
                        if team.lower() in title.lower() or team.lower() in desc.lower():
                            team_news.append(f"{title}: {desc}")
                    
                    if team_news:
                        combined = " | ".join(team_news[:3])
                        # 检查是否和缓存里的新闻一致，如果不一致才去请求 LLM (节省 token 和时间)
                        current_cached = self._cache.get(team, {}).get("news", "")
                        if combined != current_cached:
                            xg_impact = self._analyze_xg_impact_with_llm(team, combined)
                            with self._cache_lock:
                                self._cache[team] = {
                                    "timestamp": time.time(),
                                    "team": team,
                                    "news": combined,
                                    "xg_impact": xg_impact,
                                    "source": "rss_aggregator_cache",
                                    "latency_ms": 0 # 从内存读，延迟为 0
                                }
            except Exception as e:
                print(f"   -> ⚠️ [ZSA 快轨] 后台轮询异常: {e}")
                
            time.sleep(30) # 每 30 秒扫描一次

    def fetch_latest_news(self, team_name: str) -> Dict[str, Any]:
        """获取最新的突发新闻，O(1) 内存穿透，实现毫秒级套利"""
        if self.use_mock:
            return self._mock_news(team_name)

        start_t = time.perf_counter()
        
        with self._cache_lock:
            # 如果球队不在监控列表中，将其加入缓存并先返回一个默认值，让后台线程去抓
            if team_name not in self._cache:
                self._cache[team_name] = {
                    "timestamp": time.time(),
                    "team": team_name,
                    "news": "系统刚开始监听该球队，等待下一次数据面刷新...",
                    "xg_impact": 0.0,
                    "source": "rss_aggregator_cache_init",
                    "latency_ms": 0
                }
                # 立即触发一次同步抓取以防首次等待太久 (可选，为了快速响应第一次)
                threading.Thread(target=self._force_sync_fetch, args=(team_name,), daemon=True).start()
            
            result = dict(self._cache[team_name])
            
        end_t = time.perf_counter()
        result["latency_ms"] = round((end_t - start_t) * 1000, 2)
        return result

    def _force_sync_fetch(self, team_name: str):
        """仅在首次被查询时，强制做一次同步抓取填入缓存"""
        print(f"   -> 📡 [ZSA 快轨] 首次扫描 {team_name} 的情报入缓存...")
        news_items = []
        try:
            for url in self.rss_feeds:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    for item in root.findall('./channel/item'):
                        title = item.find('title').text or ""
                        desc = item.find('description').text or ""
                        if team_name.lower() in title.lower() or team_name.lower() in desc.lower():
                            news_items.append(f"{title}: {desc}")
        except Exception:
            pass

        if news_items:
            combined = " | ".join(news_items[:3])
            xg_impact = self._analyze_xg_impact_with_llm(team_name, combined)
            with self._cache_lock:
                self._cache[team_name] = {
                    "timestamp": time.time(),
                    "team": team_name,
                    "news": combined,
                    "xg_impact": xg_impact,
                    "source": "rss_aggregator_cache",
                    "latency_ms": 0
                }

    def _analyze_xg_impact_with_llm(self, team_name: str, news_text: str) -> float:
        """调用 LLM 将自然语言新闻转化为量化的 xG (预期进球) 影响"""
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
        model_name = os.environ.get("MODEL_NAME", "gpt-4o-mini")

        if not api_key:
            print("   -> ⚠️ [Social Listener] 未配置 API Key，无法量化新闻影响。")
            return 0.0

        try:
            import openai
            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            client = openai.OpenAI(**client_kwargs)

            prompt = f"""
你是专业的足球量化分析师。请评估以下关于 {team_name} 的新闻对他们本场比赛的预期进球数(xG)的影响。
新闻：{news_text}

规则：
- 如果是核心前锋受伤/红牌，xg_impact 在 -0.5 到 -1.0 之间
- 如果是防守核心受伤，不影响己方 xG，可能影响对方 xG（此处仅评估己方进球能力，故为 0.0 或轻微负数）
- 如果是核心复出或士气大振，xg_impact 在 +0.2 到 +0.5 之间
- 如果是普通新闻或无关紧要，输出 0.0

请只输出一个浮点数，不要有任何其他字符。例如: -0.5
"""
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            impact_str = response.choices[0].message.content.strip()
            # 提取出浮点数
            match = re.search(r'-?\d+\.\d+', impact_str)
            if match:
                return float(match.group())
            return float(impact_str)
        except Exception as e:
            print(f"   -> ⚠️ [Social Listener] LLM 分析异常: {e}")
            return 0.0

    def _mock_news(self, team_name: str) -> Dict[str, Any]:
        import random
        mock_news_pool = [
            {"text": f"【突发】{team_name} 核心前锋在赛前热身时大腿拉伤，已退出大名单！", "xg_impact": -0.8},
            {"text": f"【常规】{team_name} 主教练出席赛前发布会，表示全队士气高昂。", "xg_impact": 0.0}
        ]
        news = random.choice(mock_news_pool)
        return {
            "timestamp": time.time(),
            "team": team_name,
            "news": news["text"],
            "xg_impact": news["xg_impact"],
            "source": "twitter_insider_webhook",
            "latency_ms": random.randint(15, 80)
        }