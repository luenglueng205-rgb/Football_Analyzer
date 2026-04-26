import time
import os
import threading
from typing import Dict, Any
import requests
import xml.etree.ElementTree as ET
import re
import json
from openclaw_workspace.tools.paths import data_dir

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
        
        # 加载本地 SLM (Phase 2)
        self.use_local_slm = os.getenv("USE_LOCAL_SLM", "true").lower() in ("true", "1", "yes")
        self.slm_classifier = None
        if self.use_local_slm:
            try:
                from transformers import pipeline
                print("   -> 🧠 [ZSA 快轨] 正在预加载本地轻量级 NLP 模型 (Local SLM)...")
                # 使用 pipeline，自动下载并加载模型到内存。首次运行可能需要下载几百MB。
                self.slm_classifier = pipeline(
                    "zero-shot-classification", 
                    model="cross-encoder/nli-distilroberta-base",
                    device=-1 # 强制使用 CPU 保证通用性，如果需要极速可配置 mps/cuda
                )
                print("   -> ⚡ [ZSA 快轨] 本地 NLP 模型加载完毕，准备毫秒级推演！")
            except Exception as e:
                print(f"   -> ❌ [ZSA 快轨] 本地模型加载失败，将回退至云端 LLM: {e}")
                self.use_local_slm = False
        
        # 启动后台常驻轮询线程
        if not self.use_mock:
            self._polling_thread = threading.Thread(target=self._background_poll, daemon=True)
            self._polling_thread.start()
            print("   -> 🚀 [ZSA 快轨] SocialNewsListener 常驻内存守护线程已启动...")
            
        # ZSA Phase 3: 内存总线回调机制
        self._callbacks = []

        # RLEF: 动态加载 ZSA 触发阈值
        self._load_zsa_thresholds()

    def _load_zsa_thresholds(self):
        self.neg_threshold = -0.8
        self.pos_threshold = 0.5
        try:
            # 尝试从 hyperparams.json 读取
            hp_path = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "hyperparams.json")
            if os.path.exists(hp_path):
                with open(hp_path, "r", encoding="utf-8") as f:
                    params = json.load(f)
                    zsa_t = params.get("zsa_thresholds", {})
                    if "negative_impact_threshold" in zsa_t:
                        self.neg_threshold = float(zsa_t["negative_impact_threshold"])
                    if "positive_impact_threshold" in zsa_t:
                        self.pos_threshold = float(zsa_t["positive_impact_threshold"])
        except Exception as e:
            print(f"   -> ⚠️ [ZSA] 无法加载动态阈值，使用默认值: {e}")

    def register_callback(self, callback_func):
        """注册回调函数，当检测到极端情报时触发截胡"""
        self._callbacks.append(callback_func)

    def _fire_callbacks(self, team: str, news: str, impact: float):
        for cb in self._callbacks:
            try:
                # 异步执行回调，避免阻塞监听器
                threading.Thread(target=cb, args=(team, news, impact), daemon=True).start()
            except Exception as e:
                print(f"   -> ⚠️ [ZSA 快轨] 回调执行异常: {e}")

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
                            
                            # 触发内存总线截胡
                            if xg_impact <= self.neg_threshold or xg_impact >= self.pos_threshold:
                                self._fire_callbacks(team, combined, xg_impact)
                                
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
            
            # 触发内存总线截胡
            if xg_impact <= self.neg_threshold or xg_impact >= self.pos_threshold:
                self._fire_callbacks(team_name, combined, xg_impact)
                
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
        """路由调度：优先使用毫秒级本地模型"""
        if getattr(self, 'use_local_slm', False) and getattr(self, 'slm_classifier', None):
            return self._analyze_with_local_slm(team_name, news_text)
        else:
            return self._analyze_with_cloud_llm(team_name, news_text)

    def _analyze_with_local_slm(self, team_name: str, news_text: str) -> float:
        """内存穿透，极速本地推理"""
        if not self.slm_classifier:
            return 0.0
            
        try:
            start_t = time.perf_counter()
            
            # 原子标签，提升 NLI 模型的匹配度
            candidate_labels = [
                "player injury", 
                "player suspension", 
                "red card", 
                "player return from injury", 
                "team morale boost", 
                "neutral news"
            ]
            
            # 极速本地前向传播，增加 hypothesis_template 提升置信度
            result = self.slm_classifier(
                news_text, 
                candidate_labels,
                hypothesis_template="This football news is about {}."
            )
            
            top_label = result['labels'][0]
            confidence = result['scores'][0]
            
            impact = 0.0
            
            negative_labels = ["player injury", "player suspension", "red card"]
            positive_labels = ["player return from injury", "team morale boost"]
            
            # 分层阈值判定
            if top_label in negative_labels:
                if confidence > 0.55:
                    impact = -0.8
                elif confidence >= 0.40:
                    # 灰色地带兜底：结合关键词
                    if any(kw in news_text.lower() for kw in ["injur", "miss", "out", "red card", "suspend", "缺阵", "伤", "红牌"]):
                        impact = -0.8
            elif top_label in positive_labels:
                if confidence > 0.55:
                    impact = 0.3
                elif confidence >= 0.40:
                    if any(kw in news_text.lower() for kw in ["return", "back", "boost", "复出", "回归", "振奋"]):
                        impact = 0.3
            
            end_t = time.perf_counter()
            print(f"   -> ⚡ [Local SLM] 本地推理完成，耗时: {(end_t - start_t)*1000:.2f}ms | 标签: {top_label} ({confidence:.2f}) -> Impact: {impact}")
            return impact
            
        except Exception as e:
            print(f"   -> ⚠️ [Local SLM] 本地推理异常: {e}")
            return 0.0

    def _analyze_with_cloud_llm(self, team_name: str, news_text: str) -> float:
        """原有的调用云端 LLM 的逻辑"""
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

    def inject_mock_news(self, team_name: str, news_text: str, impact: float):
        """用于测试：手动注入假新闻并触发截胡"""
        with self._cache_lock:
            self._cache[team_name] = {
                "timestamp": time.time(),
                "team": team_name,
                "news": news_text,
                "xg_impact": impact,
                "source": "manual_inject",
                "latency_ms": 0
            }
        print(f"   -> 💉 [ZSA 快轨] 手动注入情报: {news_text} (Impact: {impact})")
        if impact <= self.neg_threshold or impact >= self.pos_threshold:
            self._fire_callbacks(team_name, news_text, impact)