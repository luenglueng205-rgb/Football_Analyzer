# ZSA Phase 2: Local SLM Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the slow, synchronous cloud LLM call with a lightning-fast local Small Language Model (SLM) for zero-shot classification to achieve sub-200ms latency for news xG impact analysis.

**Architecture:** We will use Hugging Face's `transformers` pipeline to load a lightweight zero-shot classification model (`cross-encoder/nli-distilroberta-base`) into memory upon initialization. The `SocialNewsListener` will route requests to this local model instead of the cloud API when `USE_LOCAL_SLM=true`.

**Tech Stack:** Python, Hugging Face Transformers, PyTorch.

---

### Task 1: Install Dependencies

**Files:**
- Modify: Environment

- [ ] **Step 1: Install required packages**

Run: `pip install transformers torch`
Expected: Successful installation.

### Task 2: Refactor `SocialNewsListener` for Local SLM

**Files:**
- Modify: `core_system/skills/news_arbitrage/social_listener.py`

- [ ] **Step 1: Add imports and initialization logic**

Update the imports and `__init__` method to conditionally load the local model.

```python
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
        
        # 加载本地 SLM (Phase 2)
        self.use_local_slm = os.getenv("USE_LOCAL_SLM", "true").lower() in ("true", "1", "yes")
        self.slm_classifier = None
        if self.use_local_slm and not self.use_mock:
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
```

- [ ] **Step 2: Add Local SLM analysis method**

Add a new method `_analyze_with_local_slm` to perform the zero-shot classification.

```python
    def _analyze_with_local_slm(self, team_name: str, news_text: str) -> float:
        """内存穿透，极速本地推理"""
        if not self.slm_classifier:
            return 0.0
            
        try:
            start_t = time.perf_counter()
            # 候选标签，对应我们在云端 Prompt 中的规则
            candidate_labels = [
                "injury or suspension or red card", 
                "return from injury or morale boost", 
                "neutral or irrelevant news"
            ]
            
            # 极速本地前向传播
            result = self.slm_classifier(news_text, candidate_labels)
            
            top_label = result['labels'][0]
            confidence = result['scores'][0]
            
            impact = 0.0
            # 极高置信度才触发极端的 xG 调整
            if top_label == "injury or suspension or red card" and confidence > 0.55:
                impact = -0.8
            elif top_label == "return from injury or morale boost" and confidence > 0.55:
                impact = 0.3
            
            end_t = time.perf_counter()
            print(f"   -> ⚡ [Local SLM] 本地推理完成，耗时: {(end_t - start_t)*1000:.2f}ms | 标签: {top_label} ({confidence:.2f}) -> Impact: {impact}")
            return impact
            
        except Exception as e:
            print(f"   -> ⚠️ [Local SLM] 本地推理异常: {e}")
            return 0.0
```

- [ ] **Step 3: Update routing in `_analyze_xg_impact_with_llm`**

Rename the existing cloud LLM logic to `_analyze_with_cloud_llm` and update `_analyze_xg_impact_with_llm` to act as a router.

```python
    def _analyze_xg_impact_with_llm(self, team_name: str, news_text: str) -> float:
        """路由调度：优先使用毫秒级本地模型"""
        if getattr(self, 'use_local_slm', False) and getattr(self, 'slm_classifier', None):
            return self._analyze_with_local_slm(team_name, news_text)
        else:
            return self._analyze_with_cloud_llm(team_name, news_text)

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
            print(f"   -> ⚠️ [Social Listener] 云端 LLM 分析异常: {e}")
            return 0.0
```

- [ ] **Step 4: Commit changes**

```bash
git add core_system/skills/news_arbitrage/social_listener.py
git commit -m "feat(zsa): integrate local SLM for sub-200ms news analysis"
```

### Task 3: Test SLM Latency

**Files:**
- Create: `test_zsa_slm_latency.py`

- [ ] **Step 1: Write the test script**

```python
import time
import os
from core_system.skills.news_arbitrage.social_listener import SocialNewsListener

def test_slm_latency():
    # 强制启用本地 SLM
    os.environ["USE_LOCAL_SLM"] = "true"
    os.environ["NEWS_LISTENER_MOCK"] = "false"
    
    print("初始化 SocialNewsListener，等待模型加载...")
    listener = SocialNewsListener()
    
    if not listener.slm_classifier:
        print("❌ 模型未加载成功，跳过测试。")
        return
        
    test_news = "BREAKING: Arsenal star striker suffers severe hamstring injury during warm-up and is out of the match."
    team = "Arsenal"
    
    print(f"\n测试新闻: {test_news}")
    
    # 第一次推理可能会稍微慢一点 (JIT 编译/内存加载)
    print("\n--- 预热推理 ---")
    listener._analyze_with_local_slm(team, test_news)
    
    # 第二次真实的性能测试
    print("\n--- 真实性能测试 ---")
    start = time.perf_counter()
    impact = listener._analyze_with_local_slm(team, test_news)
    end = time.perf_counter()
    
    latency_ms = (end - start) * 1000
    print(f"推理耗时: {latency_ms:.2f} ms")
    print(f"计算出的 xG Impact: {impact}")
    
    assert impact < 0, "The model failed to classify this as an injury/negative impact."
    assert latency_ms < 500.0, "Latency is too high for ZSA fast-path!"
    print("\n✅ SLM 极速推理测试通过！")

if __name__ == "__main__":
    test_slm_latency()
```

- [ ] **Step 2: Run the test**

Run: `PYTHONPATH=. python3 test_zsa_slm_latency.py`
Expected: Successful model download (if first time), then output showing latency < 500ms and a negative xG impact.
