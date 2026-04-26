# ZSA Phase 3: Front-running Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the execution layer of the Zero-Shot Arbitrage (ZSA) module, enabling the system to bypass the complex LangGraph reasoning and immediately place a front-running bet when critical news is detected.

**Architecture:** We will introduce a callback mechanism in `SocialNewsListener` that triggers when extreme `xg_impact` values are detected (e.g., `<= -0.8`). A new `ZSAFrontRunner` component will listen to these events, match the team with a simulated live odds feed, and directly call `BettingLedger.execute_bet` to capitalize on the information gap before bookmakers adjust their odds.

**Tech Stack:** Python, Event-driven callbacks.

---

### Task 1: Add Callback Mechanism to `SocialNewsListener`

**Files:**
- Modify: `core_system/skills/news_arbitrage/social_listener.py`

- [ ] **Step 1: Add callback registration**

Update `__init__` to initialize a list of callbacks and add a method to register them.

```python
        # 启动后台常驻轮询线程
        if not self.use_mock:
            self._polling_thread = threading.Thread(target=self._background_poll, daemon=True)
            self._polling_thread.start()
            print("   -> 🚀 [ZSA 快轨] SocialNewsListener 常驻内存守护线程已启动...")
            
        # ZSA Phase 3: 内存总线回调机制
        self._callbacks = []

    def register_callback(self, callback_func):
        """注册回调函数，当检测到极端情报时触发截胡"""
        self._callbacks.append(callback_func)
```

- [ ] **Step 2: Trigger callbacks on extreme impact**

Update `_background_poll` and `_force_sync_fetch` to check the impact and fire callbacks. Since we only want to fire it once per piece of news, we do it right after calculating the impact.

Find this block in `_background_poll`:
```python
                        if combined != current_cached:
                            xg_impact = self._analyze_xg_impact_with_llm(team, combined)
                            with self._cache_lock:
```

Change it to:
```python
                        if combined != current_cached:
                            xg_impact = self._analyze_xg_impact_with_llm(team, combined)
                            
                            # 触发内存总线截胡
                            if xg_impact <= -0.8 or xg_impact >= 0.5:
                                self._fire_callbacks(team, combined, xg_impact)
                                
                            with self._cache_lock:
```

Find this block in `_force_sync_fetch`:
```python
        if news_items:
            combined = " | ".join(news_items[:3])
            xg_impact = self._analyze_xg_impact_with_llm(team_name, combined)
            
            # 触发内存总线截胡
            if xg_impact <= -0.8 or xg_impact >= 0.5:
                self._fire_callbacks(team_name, combined, xg_impact)
                
            with self._cache_lock:
```

Add the `_fire_callbacks` method:
```python
    def _fire_callbacks(self, team: str, news: str, impact: float):
        for cb in self._callbacks:
            try:
                # 异步执行回调，避免阻塞监听器
                threading.Thread(target=cb, args=(team, news, impact), daemon=True).start()
            except Exception as e:
                print(f"   -> ⚠️ [ZSA 快轨] 回调执行异常: {e}")
```

- [ ] **Step 3: Update `_mock_news` to support triggering callbacks in mock mode**

Since we test with `NEWS_LISTENER_MOCK=true` sometimes, let's add a method to manually inject mock news and trigger callbacks.

```python
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
        if impact <= -0.8 or impact >= 0.5:
            self._fire_callbacks(team_name, news_text, impact)
```

### Task 2: Create `ZSAFrontRunner` Execution Engine

**Files:**
- Create: `core_system/skills/news_arbitrage/front_runner.py`

- [ ] **Step 1: Write the `ZSAFrontRunner` class**

This class connects to `BettingLedger` and `GrandmasterRouter`. It maintains a simulated live odds feed.

```python
import time
from typing import Dict
from core_system.tools.betting_ledger import BettingLedger
from core_system.agents.grandmaster_router import GrandmasterRouter
from core_system.skills.news_arbitrage.social_listener import SocialNewsListener

class ZSAFrontRunner:
    """
    Zero-Shot Arbitrage (ZSA) 截胡执行器。
    监听 SocialNewsListener 的内存总线，一旦发现改变基本面的重大情报（如核心受伤），
    绕过所有慢速的 LangGraph 节点和复杂数学计算，直接向底层账本发起做空出票请求。
    """
    def __init__(self, listener: SocialNewsListener):
        self.listener = listener
        self.ledger = BettingLedger()
        self.router = GrandmasterRouter()
        
        # 注册回调
        self.listener.register_callback(self.handle_extreme_news)
        
        # 模拟的实时走地盘口 (In-Play Live Odds Feed)
        # 实际生产中这里会是一个高速 WebSocket 订阅庄家盘口
        self.live_markets = {
            "Arsenal": {
                "match_id": "EPL_LIVE_1001",
                "opponent": "Chelsea",
                "odds": {
                    "home_win": 2.10,
                    "draw": 3.40,
                    "away_win": 3.50  # 切尔西胜
                },
                "is_home": True
            },
            "Manchester City": {
                "match_id": "EPL_LIVE_1002",
                "opponent": "Liverpool",
                "odds": {
                    "home_win": 1.80,
                    "draw": 3.60,
                    "away_win": 4.20
                },
                "is_home": True
            }
        }
        
    def handle_extreme_news(self, team: str, news: str, impact: float):
        print(f"\n🚨🚨🚨 [ZSA 截胡系统触发] 🚨🚨🚨")
        print(f"   -> 接收到极端情报: {team} | Impact: {impact}")
        print(f"   -> 准备进行内存总线阻断与极速执行...")
        
        market = self.live_markets.get(team)
        if not market:
            print(f"   -> ❌ 未找到 {team} 的走地盘口，取消截胡。")
            return
            
        start_t = time.perf_counter()
        
        # 极速决策逻辑
        if impact <= -0.8:
            # 球队遭遇重大负面打击，果断做空 (买对手赢)
            target_selection = "away_win" if market["is_home"] else "home_win"
            target_team = market["opponent"]
            target_odds = market["odds"][target_selection]
            stake = 500.0  # 固定截胡仓位
            
            print(f"   -> ⚡ 决策: {team} 遭遇重创，极速做空！买入 {target_team} 胜 (赔率 {target_odds})")
            
            # 极速出票 (绕过图流转)
            res = self.ledger.execute_bet(
                agent_id="zsa_front_runner",
                match_id=market["match_id"],
                lottery_type="jingcai",  # 使用竞彩单关模拟
                selection=f"WDL_{target_selection}",
                odds=target_odds,
                stake=stake
            )
            
            end_t = time.perf_counter()
            latency = (end_t - start_t) * 1000
            
            if res.get("status") == "success":
                print(f"   -> ✅ [ZSA 截胡成功] 耗时: {latency:.2f}ms | 凭证: {res['ticket_code']} | 余额: ${res['remaining_balance']:.2f}")
                # 物理路由分发
                self.router.dispatch_matches({}, {f"WDL_{target_selection}": 0.99}, {"jingcai_odds": {f"WDL_{target_selection}": target_odds}})
            else:
                print(f"   -> ❌ [ZSA 截胡失败] 耗时: {latency:.2f}ms | 原因: {res.get('message')}")

```

### Task 3: Integration Test for ZSA Front-Running

**Files:**
- Create: `test_zsa_front_running.py`

- [ ] **Step 1: Write the test script**

```python
import time
import os
from core_system.skills.news_arbitrage.social_listener import SocialNewsListener
from core_system.skills.news_arbitrage.front_runner import ZSAFrontRunner
from core_system.tools.betting_ledger import BettingLedger

def test_front_running():
    # 使用本地 SLM，关闭真实轮询
    os.environ["USE_LOCAL_SLM"] = "true"
    os.environ["NEWS_LISTENER_MOCK"] = "true"
    
    print("1. 初始化组件...")
    listener = SocialNewsListener(use_mock=True)
    runner = ZSAFrontRunner(listener)
    ledger = BettingLedger()
    
    # 充值 ZSA 专用资金池
    ledger.reset_economy(agent_id="zsa_front_runner", initial_balance=10000.0)
    
    print("\n2. 模拟系统正在安静运行...")
    time.sleep(1)
    
    print("\n3. 突然！突发新闻爆发 (Arsenal star injured)...")
    test_news = "BREAKING: Arsenal star striker suffers severe hamstring injury during warm-up and is out of the match."
    
    # 先做一次预热推理，防止第一次加载耗时影响我们观察截胡延迟
    listener._analyze_with_local_slm("Arsenal", test_news)
    
    print("\n--- 真实事件注入 ---")
    # 这会触发 SLM 推理，然后发现 impact <= -0.8，触发回调
    impact = listener._analyze_with_local_slm("Arsenal", test_news)
    listener.inject_mock_news("Arsenal", test_news, impact)
    
    # 给异步线程一点时间执行
    time.sleep(1)
    
    print("\n4. 验证账本...")
    status = ledger.check_bankroll(agent_id="zsa_front_runner")
    print(f"ZSA Agent 余额: ${status['current_bankroll']:.2f}")
    assert status['current_bankroll'] == 9500.0, "Bet was not placed!"
    print("\n✅ ZSA Phase 3 内存总线截胡测试通过！")

if __name__ == "__main__":
    test_front_running()
```

- [ ] **Step 2: Run the test**

Run: `PYTHONPATH=. python3 test_zsa_front_running.py`
Expected: The test should output the `🚨🚨🚨 [ZSA 截胡系统触发] 🚨🚨🚨` logs, show a fast latency (< 100ms for the execution part), and confirm the bet was placed by deducting $500 from the balance.
