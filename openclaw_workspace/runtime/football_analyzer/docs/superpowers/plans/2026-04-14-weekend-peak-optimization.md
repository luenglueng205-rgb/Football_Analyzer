# Weekend Peak Optimization (周末洪峰工业级并发改造) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 7x24 守护进程，引入“轻量级初筛漏斗”和“生产者-消费者”协程池，确保系统在面临周末 200+ 场并发赛程时，既不会超时卡死，也不会触发 API 速率熔断。

**Architecture:** 
1. **Pre-Filter Funnel**: 编写 `PreFilter` 工具，使用极低成本的计算（如仅调取免费的赔率 API 或计算主客胜率极差）快速剔除“野鸡比赛”和“蚊子肉赔率”，将 200 场缩减至高价值的 20-30 场。
2. **Worker Pool**: 修改 `market_sentinel.py`，使用 `asyncio.Queue` 配合固定数量（如 3-5 个）的 worker tasks 进行消费，替代原有的无限并发或死板的 for 循环串行。

**Tech Stack:** `asyncio`

---

### Task 1: 建立高价值比赛漏斗过滤器 (Pre-Filter)

**Files:**
- Create: `tools/pre_filter.py`

- [ ] **Step 1: 编写初筛过滤类**

```python
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class MatchPreFilter:
    """
    周末洪峰初筛漏斗：在不消耗大模型 Token 的前提下，快速过滤掉无投资价值的比赛。
    """
    def __init__(self):
        # 预设五大联赛等高价值赛事白名单，或者通过黑名单过滤
        self.top_leagues = ["英超", "西甲", "意甲", "德甲", "法甲", "欧冠", "欧罗巴"]
        self.ignore_keywords = ["女足", "青年", "U21", "U19", "友谊赛", "后备"]

    def is_high_value_match(self, match: Dict) -> bool:
        """
        判断比赛是否值得动用昂贵的 SyndicateOS 进行深度分析
        """
        home = match.get("home_team", "")
        away = match.get("away_team", "")
        league = match.get("league", "")
        
        # 1. 过滤野鸡赛事关键字
        combined_text = f"{home} {away} {league}"
        for kw in self.ignore_keywords:
            if kw in combined_text:
                logger.info(f"过滤: {home} vs {away} (原因: 包含忽略关键字 '{kw}')")
                return False
                
        # 这里还可以加入初步的赔率过滤（比如调用一次免费 API，发现胜赔 1.05 直接抛弃）
        # 出于演示，我们假设经过关键字过滤的都是有价值的
        return True

    def filter_matches(self, matches: List[Dict]) -> List[Dict]:
        """批量过滤"""
        return [m for m in matches if self.is_high_value_match(m)]
```

- [ ] **Step 2: 编写测试脚本验证过滤器**

```bash
cat << 'EOF' > test_filter.py
from tools.pre_filter import MatchPreFilter

matches = [
    {"home_team": "曼联", "away_team": "阿森纳", "league": "英超"},
    {"home_team": "某某U21", "away_team": "青年队", "league": "友谊赛"},
    {"home_team": "皇家马德里", "away_team": "巴塞罗那", "league": "西甲"}
]

f = MatchPreFilter()
filtered = f.filter_matches(matches)
print(f"Original: {len(matches)}, Filtered: {len(filtered)}")
assert len(filtered) == 2
EOF
python3 test_filter.py
```
Expected: PASS (输出 Original: 3, Filtered: 2)

### Task 2: 重构 Market Sentinel 使用协程池

**Files:**
- Modify: `market_sentinel.py`

- [ ] **Step 1: 引入 Queue 和 Worker 机制**

完全重写 `MarketSentinel` 类，实现生产者-消费者模型。

```python
import asyncio
import logging
from typing import List, Dict
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

    async def run_forever(self):
        logging.info("==================================================")
        logging.info("🛡️ 7x24 Market Sentinel (Worker Pool Edition)")
        logging.info("==================================================")
        
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
```

- [ ] **Step 2: 编写测试脚本模拟周末洪峰**

```bash
cat << 'EOF' > test_peak.py
import asyncio
from market_sentinel import MarketSentinel
from tools.analyzer_api import AnalyzerAPI
from unittest.mock import patch

# 模拟 200 场周末洪峰数据
def mock_get_live_fixtures():
    matches = []
    # 构造 180 场野鸡比赛 (带U21, 女足等关键字)
    for i in range(180):
        matches.append({"home_team": f"野鸡队{i} U21", "away_team": f"对手{i} U21", "status": "upcoming"})
    # 构造 20 场焦点战
    for i in range(20):
        matches.append({"home_team": f"豪门{i}", "away_team": f"强队{i}", "status": "upcoming"})
    return matches

async def run_test():
    with patch.object(AnalyzerAPI, 'get_live_fixtures', side_effect=mock_get_live_fixtures):
        # 创建一个带有 3 个 worker 的 Sentinel，覆盖它的 process_match 防止真消耗 Token
        sentinel = MarketSentinel(max_workers=3)
        
        async def mock_process(home, away, desc):
            await asyncio.sleep(0.5) # 模拟处理耗时
            return {"final_decision": "mock decision"}
            
        sentinel.os_system.process_match = mock_process
        
        # 只跑一轮测试
        opps = await sentinel._fetch_market_scan()
        for opp in opps:
            await sentinel.queue.put(opp)
            
        # 启动 workers 并等待队列清空
        workers = [asyncio.create_task(sentinel._worker(i)) for i in range(sentinel.max_workers)]
        await sentinel.queue.join()
        
        # 取消 workers
        for w in workers:
            w.cancel()
            
        print("✅ 周末洪峰并发测试完成！")

if __name__ == "__main__":
    asyncio.run(run_test())
EOF
python3 test_peak.py
```
Expected: PASS (终端应打印：初筛过滤掉 180 场，剩余 20 场投递给队列。3 个 Worker 并发消费这 20 场比赛，大概 3-4 秒后全部消费完毕)。

### Task 3: 清理旧代码并提交

**Files:**
- None

- [ ] **Step 1: Commit**

```bash
rm test_filter.py test_peak.py
git add tools/pre_filter.py market_sentinel.py
git commit -m "feat(p4): optimize market sentinel with pre-filter funnel and worker pool for weekend peaks"
```