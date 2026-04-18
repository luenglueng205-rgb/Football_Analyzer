# AI-Native Cognitive Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Shift the core architecture from hardcoded Python routing to pure AI-Native cognitive reasoning, implementing League Personas, 16-Market Strategic Allocation, dynamic Web Intelligence, and 500.com-style simulated tickets.

**Architecture:** The LLM Brain (`AINativeCoreAgent`) will be upgraded with a "Cognitive Prompt Framework". It will forcefully fetch league characteristics via a new `LeagueProfiler` tool, gather breaking news via an `IntelligenceGatherer` tool, and output its reasoning through a `16_market_strategist` framework. Finally, the ticket output will be styled like a 500.com simulator instead of a physical printout.

**Tech Stack:** Python, OpenAI API, DuckDuckGo Search (ddgs), Markdown Formatting.

---

### Task 1: Implement League Profiler Tool

**Files:**
- Create: `standalone_workspace/tools/league_profiler.py`
- Modify: `standalone_workspace/tools/tool_registry_v2.py`
- Test: `standalone_workspace/tests/test_league_profiler.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from tools.league_profiler import get_league_persona

def test_league_profiler_returns_persona():
    result = get_league_persona("Premier League")
    assert "persona" in result
    assert "variance" in result
    assert "tactical_style" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_league_profiler.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
import json

def get_league_persona(league_name: str) -> str:
    """
    Retrieve the tactical persona, historical variance, and referee leniency of a specific football league.
    Use this to adjust Poisson distributions and Kelly Criterion calculations.
    """
    profiles = {
        "premier league": {"persona": "High intensity, physical, fast transitions.", "variance": "High", "tactical_style": "Attacking, high pressing."},
        "serie a": {"persona": "Tactical, defensive rigidity, slow buildup.", "variance": "Low", "tactical_style": "Defensive blocks, counter-attack."},
        "la liga": {"persona": "Technical, possession-based.", "variance": "Medium", "tactical_style": "Tiki-taka, high ball retention."},
        "eredivisie": {"persona": "Open play, development league, poor defending.", "variance": "Very High", "tactical_style": "Total football, high scoring."},
        "default": {"persona": "Standard professional league.", "variance": "Medium", "tactical_style": "Balanced."}
    }
    
    key = league_name.lower()
    profile = profiles.get(key, profiles["default"])
    
    return json.dumps({
        "league": league_name,
        "profile": profile,
        "ai_instruction": f"Adjust your prediction model considering this league has {profile['variance']} variance and a {profile['tactical_style']} style."
    }, ensure_ascii=False)
```

- [ ] **Step 4: Register tool in registry**
Update `standalone_workspace/tools/tool_registry_v2.py` to include `get_league_persona` in the `TOOL_MAPPING` and `get_openai_tools()`.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_league_profiler.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add standalone_workspace/tools/league_profiler.py standalone_workspace/tools/tool_registry_v2.py standalone_workspace/tests/test_league_profiler.py
git commit -m "feat(ai-native): add league profiler tool for cognitive context"
```

### Task 2: Implement Dynamic Web Intelligence Gatherer

**Files:**
- Create: `standalone_workspace/tools/intelligence_gatherer.py`
- Modify: `standalone_workspace/tools/tool_registry_v2.py`

- [ ] **Step 1: Write minimal implementation**

```python
import json
from duckduckgo_search import DDGS
import logging

logger = logging.getLogger(__name__)

def gather_match_intelligence(team_a: str, team_b: str) -> str:
    """
    Search the web for breaking news, injuries, suspensions, or weather conditions for a specific match.
    The AI should use this to adjust the baseline quantitative model.
    """
    query = f"{team_a} {team_b} injuries suspensions news"
    results = []
    
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=3):
                results.append(r.get('body', ''))
    except Exception as e:
        logger.error(f"DDGS Search failed: {e}")
        return json.dumps({"error": "Failed to gather live intelligence. Proceed with historical data only."})
        
    if not results:
        return json.dumps({"insight": "No significant breaking news found."})
        
    return json.dumps({
        "query": query,
        "breaking_news": results,
        "ai_instruction": "Analyze the sentiment of this news. If key players are injured, severely downgrade that team's attacking or defensive strength in your Poisson model."
    }, ensure_ascii=False)
```

- [ ] **Step 2: Register tool in registry**
Update `standalone_workspace/tools/tool_registry_v2.py` to include `gather_match_intelligence`.

- [ ] **Step 3: Commit**

```bash
git add standalone_workspace/tools/intelligence_gatherer.py standalone_workspace/tools/tool_registry_v2.py
git commit -m "feat(ai-native): add dynamic web intelligence gatherer"
```

### Task 3: Implement 500.com Simulated Ticket Formatter

**Files:**
- Create: `standalone_workspace/tools/simulated_ticket.py`
- Modify: `standalone_workspace/tools/tool_registry_v2.py`

- [ ] **Step 1: Write minimal implementation**

```python
import json

def generate_simulated_ticket(match: str, play_type: str, selection: str, odds: float, stake: float, confidence: float, reasoning: str) -> str:
    """
    Generate a 500.com style simulated bet slip in Markdown format.
    Instead of physical printing, this returns a beautiful virtual ticket for the user.
    """
    expected_return = stake * odds
    
    markdown_ticket = f"""
### 🎟️ 500.com 模拟选号单 (Simulated Ticket)

| 赛事 (Match) | 玩法 (Market) | 选项 (Selection) | 赔率 (Odds) | 投入 (Stake) | 预计回报 (Return) |
|-------------|---------------|------------------|-------------|-------------|-------------------|
| **{match}** | `{play_type}` | **{selection}**  | {odds:.2f}  | ¥{stake:.2f} | **¥{expected_return:.2f}** |

- **🧠 AI 信心指数 (Confidence)**: {confidence * 100:.1f}%
- **💡 策略大脑洞察 (Strategist Reasoning)**: {reasoning}

*注：本单为 AI 原生模拟选号，非真实出票。*
"""
    return json.dumps({"simulated_ticket_markdown": markdown_ticket}, ensure_ascii=False)
```

- [ ] **Step 2: Register tool in registry**
Update `standalone_workspace/tools/tool_registry_v2.py` to include `generate_simulated_ticket`.

- [ ] **Step 3: Commit**

```bash
git add standalone_workspace/tools/simulated_ticket.py standalone_workspace/tools/tool_registry_v2.py
git commit -m "feat(ai-native): add 500.com style simulated ticket formatter"
```

### Task 4: Upgrade AINativeCoreAgent Prompts & Workflow

**Files:**
- Modify: `standalone_workspace/agents/ai_native_core.py`

- [ ] **Step 1: Rewrite System Prompt and Process Loop**
Modify `standalone_workspace/agents/ai_native_core.py` to inject the new cognitive framework. Remove the physical QR code instructions.

```python
# Replace the prompt generation section in process() with:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"请为我深度量化分析这场比赛：主队 '{home}' 对阵 客队 '{away}'。当前彩种为：'{lottery_desc}'。\n"
                                         f"【AI-Native 认知升维指令】：\n"
                                         f"1. 【联赛特征大脑】：你必须首先调用 get_league_persona 了解该联赛的战术风格和方差特性。\n"
                                         f"2. 【全网动态感知】：你必须调用 gather_match_intelligence 挖掘最新的伤停、天气或突发新闻。\n"
                                         f"3. 【16种玩法策略师】：不要死板地只预测胜平负！根据你收集的联赛特征和情报，自主决定这16种玩法中哪一种（如总进球、半全场、让球）拥有最高的 EV（期望值）和最低的方差风险。\n"
                                         f"4. 【模拟选号】：一旦你确定了最高价值的玩法策略，调用 generate_simulated_ticket 生成 500.com 风格的模拟选号单，直接展示给用户，无需调用物理出票工具。\n"
                                         f"请展示你作为顶级 AI 策略师的推演过程！"}
        ]
```

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/agents/ai_native_core.py
git commit -m "feat(ai-native): upgrade LLM brain with cognitive framework and simulated ticket"
```
