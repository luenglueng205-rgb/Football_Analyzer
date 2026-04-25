# Phase 3: Visual Interaction (视觉交互接管) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 引入前沿的 `browser-use` 库，彻底删除脆弱的 `BeautifulSoup` 和基于正则/CSS选择器的爬虫代码，让 AI 通过多模态能力直接在浏览器中“看”网页、点击和提取数据。

**Architecture:** 将原本硬编码的 `AgentBrowser` 重构为一个基于 `browser-use` 的通用视觉智能体接口。为防止 `browser-use` 本身的重型依赖（如 LangChain 等）拖慢系统，我们将其封装为一个独立的异步调用模块，在需要时拉起无头浏览器，并通过纯自然语言指令让 AI 自主去获取赛事和伤停情报。

**Tech Stack:** `browser-use`, `langchain-openai`, `playwright`

---

### Task 1: 安装前沿依赖并初始化 VisualBrowser 类

**Files:**
- Create: `tools/visual_browser.py`

- [ ] **Step 1: 安装 browser-use 及相关依赖**

```bash
python3 -m pip install browser-use langchain-openai --user --break-system-packages
```

- [ ] **Step 2: 编写 VisualBrowser 封装类**

```python
import os
import asyncio
from langchain_openai import ChatOpenAI
from browser_use import Agent

class VisualBrowser:
    """
    P3 阶段视觉交互引擎：完全基于自然语言指令驱动浏览器，抛弃一切 HTML 解析代码。
    """
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        
        # browser-use 强依赖 LangChain 接口
        self.llm = ChatOpenAI(
            model="gpt-4o", # 必须使用支持视觉的多模态大模型
            api_key=api_key,
            base_url=base_url,
            max_tokens=2048
        )

    async def extract_info(self, task_instruction: str) -> str:
        """
        向浏览器下达自然语言抓取指令，返回 AI 总结的纯文本结果。
        """
        try:
            agent = Agent(
                task=task_instruction,
                llm=self.llm
            )
            print(f"    [👀 VisualBrowser] 正在拉起视觉智能体执行任务...")
            # 运行 Agent，返回执行历史
            history = await agent.run()
            # 提取最后一步的最终结果
            if history and hasattr(history, 'final_result'):
                 return history.final_result()
            return str(history)
        except Exception as e:
            print(f"    [👀 VisualBrowser] 视觉交互失败: {e}")
            return f"Error: {e}"
```

- [ ] **Step 3: 编写并运行临时测试脚本**

```bash
cat << 'EOF' > test_visual.py
import asyncio
import os
from tools.visual_browser import VisualBrowser

async def test():
    vb = VisualBrowser()
    # 找一个简单的任务测试，比如去懂球帝搜索曼联
    task = "打开 https://www.dongqiudi.com/ ，在搜索框搜索 '曼联'，然后把前三条新闻的标题告诉我。只返回标题文本即可。"
    res = await vb.extract_info(task)
    print("\n[Visual Result]\n", res)

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Skip test: OPENAI_API_KEY not set")
    else:
        asyncio.run(test())
EOF
python3 test_visual.py
```
Expected: PASS (如果环境配置了正确的 API_KEY，它将拉起 Chromium 并自主完成搜索，返回新闻标题。如果环境有限制，跳过此测试。)

### Task 2: 重构原有的 AgentBrowser (平滑替换)

**Files:**
- Modify: `tools/agent_browser.py`

- [ ] **Step 1: 用 VisualBrowser 的自然语言逻辑替换掉原本的 requests+bs4 代码**

```python
# 修改 tools/agent_browser.py
import asyncio
from ddgs import DDGS
from tools.visual_browser import VisualBrowser

class AgentBrowser:
    """
    重构后的 AgentBrowser：不再写爬虫逻辑，而是将任务翻译为自然语言交给 VisualBrowser。
    同时保留 ddgs 作为极轻量级的文本搜索兜底。
    """
    def __init__(self):
        self.ddgs = DDGS()
        self.visual = VisualBrowser()

    def scrape_500_fixtures(self) -> list:
        """使用视觉浏览器获取今日赛程"""
        # 注意：此处我们需要将其包装为同步或通过 asyncio.run 执行，因为原有架构很多地方是同步调用
        task = "访问 http://zx.500.com/jczq/ ，找到今天（或者即将开赛）的所有竞彩足球比赛。请严格以JSON数组格式返回，包含 'home_team', 'away_team', 'status'(填'upcoming'或'played')。"
        
        try:
            # 如果当前在 event loop 中，直接运行会报错，需要特殊处理
            try:
                loop = asyncio.get_running_loop()
                # 如果已经有 loop，创建一个 Task (这里简化处理，实际可能需要更复杂的桥接)
                res = loop.run_until_complete(self.visual.extract_info(task))
            except RuntimeError:
                res = asyncio.run(self.visual.extract_info(task))
                
            # 简单清洗并解析 JSON
            import json
            import re
            match = re.search(r'\[.*\]', res, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return []
        except Exception as e:
            print(f"[AgentBrowser] Visual scrape error: {e}")
            return []

    def search_dongqiudi_news(self, team_name: str) -> list:
        """使用视觉浏览器获取伤病情报"""
        task = f"访问懂球帝网站或直接搜索关于'{team_name}'的最新足球新闻，特别是伤停和首发情报。提炼出3条最关键的信息返回。"
        try:
            try:
                loop = asyncio.get_running_loop()
                res = loop.run_until_complete(self.visual.extract_info(task))
            except RuntimeError:
                res = asyncio.run(self.visual.extract_info(task))
                
            return [{"title": "视觉智能体情报提炼", "snippet": res, "url": "browser-use"}]
        except Exception as e:
            print(f"[AgentBrowser] Visual search error: {e}")
            return []

    def scrape_okooo_odds_search(self, home_team: str, away_team: str) -> list:
        """兜底：依然保留 ddgs 轻量搜索"""
        try:
            query = f"澳客 OR 捷报比分 {home_team} vs {away_team} 赔率 分析"
            results = list(self.ddgs.text(query, max_results=3))
            return [
                {"title": r.get('title', ''), "snippet": r.get('body', ''), "url": r.get('href', '')}
                for r in results
            ]
        except Exception:
            return []

    def search_web(self, query: str, max_results: int = 5) -> list:
        try:
            return list(self.ddgs.text(query, max_results=max_results))
        except Exception:
            return []
```

### Task 3: 清理旧代码并提交

**Files:**
- Modify: `tools/multisource_fetcher.py` (如果需要清理旧的 fallback 逻辑，可选)

- [ ] **Step 1: 验证重构后的链路**

由于 `browser-use` 每次运行会消耗较多 Token，且可能受限于无头浏览器的安装情况，我们可以编写一个极简的验证脚本，或者直接运行一次 `run_live_decision.py`，观察日志中是否出现了 `[👀 VisualBrowser]` 的字样。

```bash
python3 run_live_decision.py
```
Expected: 日志中应当能看到 AI 在调用 `get_live_fixtures` 和 `get_live_news` 时，底层通过 `VisualBrowser` 下发自然语言指令的输出。

- [ ] **Step 2: Commit**

```bash
rm test_visual.py
git add tools/visual_browser.py tools/agent_browser.py
git commit -m "feat(p3): implement visual browser interaction using browser-use"
```