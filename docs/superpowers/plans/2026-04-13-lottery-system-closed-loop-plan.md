# 体育彩票多玩法智能推荐系统改造计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立一个以体彩官方数据为基准的“当天赛事获取 → 玩法识别 → 组合生成”全自动智能分析闭环，严格隔离竞彩、北单、传统足彩。

**Architecture:** 
采用混合架构 (Hybrid Architecture)：
1. 数据层 (`get_today_offers.py`)：使用体彩官方接口(i.sporttery.cn)及高稳备用源抓取当天各彩种在售赛事池。
2. 引擎层 (`play_type_models.py` & `lottery_math_engine.py`)：对当天赛事进行全玩法(16种)的概率与EV计算，生成候选集。
3. Agent层 (`atomic_skills.py` & `SOP_PROMPT.md`)：LLM 在候选集基础上，严格按彩种规则进行组合搜索（如竞彩混合过关、北单博冷、传统任九胆拖），并由算奖引擎兜底校验。

**Tech Stack:** Python, Requests, BeautifulSoup, Scipy, LLM Function Calling

---

### Task 1: 建立统一的“当天在售赛事”获取模块 (Data Fetching)

**Files:**
- Create: `analyzer/football-lottery-analyzer/data_fetch/get_today_offers.py`

- [x] **Step 1: 编写抓取竞彩赛事的基础框架**
创建文件并实现基于体彩官方 API 的竞彩赛事抓取。

```python
import requests
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TodayOffersScraper:
    """获取当天体彩各彩种在售赛事"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
    def get_jingcai_matches(self) -> List[Dict]:
        """获取竞彩足球当天在售赛事 (胜平负/让球)"""
        try:
            # 官方API，包含 hhad(让球) 和 had(不让球)
            url = "https://i.sporttery.cn/api/fb_match_info/get_matches?poolcast=2&tzc=1"
            res = requests.get(url, headers=self.headers, timeout=10)
            data = res.json()
            
            if data.get("status", {}).get("code") != 0:
                logger.error("体彩官方API返回异常")
                return []
                
            matches = []
            match_list = data.get("result", {}).get("matchList", [])
            
            for m in match_list:
                # 提取关键信息
                match_info = {
                    "match_id": m.get("matchId"),
                    "match_num_str": m.get("matchNumStr"), # 如 周三001
                    "league": m.get("leagueNameAbbr"),
                    "home_team": m.get("homeTeamNameAbbr"),
                    "away_team": m.get("awayTeamNameAbbr"),
                    "sell_status": m.get("matchStatus"), # Selling
                    "start_time": m.get("matchDate") + " " + m.get("matchTime"),
                    "odds": {}
                }
                
                # 提取不让球胜平负
                had = m.get("oddsList", {}).get("had")
                if had:
                    match_info["odds"]["SPF"] = {
                        "h": float(had.get("h", 0)),
                        "d": float(had.get("d", 0)),
                        "a": float(had.get("a", 0))
                    }
                    
                # 提取让球胜平负
                hhad = m.get("oddsList", {}).get("hhad")
                if hhad:
                    match_info["handicap"] = int(hhad.get("goalline", 0))
                    match_info["odds"]["RQSPF"] = {
                        "h": float(hhad.get("h", 0)),
                        "d": float(hhad.get("d", 0)),
                        "a": float(hhad.get("a", 0))
                    }
                    
                matches.append(match_info)
                
            return matches
        except Exception as e:
            logger.error(f"获取竞彩赛事失败: {e}")
            return []
```

- [x] **Step 2: 补充北单和传统足彩的占位方法 (Mock/Fallback)**

```python
    def get_beidan_matches(self) -> List[Dict]:
        """获取北京单场当天在售赛事 (暂使用模拟数据或第三方备用源)"""
        # 北单官方接口较难直接抓取，这里预留接口，实战可接入 500.com 或 澳客北单页
        # 返回结构与竞彩类似，但需标记 lottery_type = "beidan"
        return [{"note": "北单抓取待接入真实源", "lottery_type": "beidan"}]
        
    def get_traditional_matches(self, issue: str = "") -> Dict:
        """获取传统足彩(如14场/任九)当期对阵"""
        # 传统足彩按期(issue)发售，实战可抓取 500.com 胜负彩页面
        return {"issue": issue, "matches": [], "lottery_type": "traditional"}
        
    def get_today_offers(self, lottery_type: str = "jingcai") -> List[Dict]:
        """统一获取入口"""
        if lottery_type == "jingcai":
            return self.get_jingcai_matches()
        elif lottery_type == "beidan":
            return self.get_beidan_matches()
        elif lottery_type == "traditional":
            return self.get_traditional_matches().get("matches", [])
        else:
            raise ValueError(f"不支持的彩种: {lottery_type}")
```

- [x] **Step 3: 测试模块运行正常**
在文件末尾添加简单的测试代码并运行。

```python
if __name__ == "__main__":
    scraper = TodayOffersScraper()
    matches = scraper.get_today_offers("jingcai")
    print(f"成功获取 {len(matches)} 场竞彩在售比赛")
    if matches:
        print(json.dumps(matches[0], ensure_ascii=False, indent=2))
```

Run: `python3 analyzer/football-lottery-analyzer/data_fetch/get_today_offers.py`
Expected: 成功打印出今天在售的一场竞彩比赛信息。

### Task 2: 将当天赛事模块原子化，暴露给 LLM

**Files:**
- Modify: `agent/openclaw-football-lottery-agent/football-lottery-analyst/tools/atomic_skills.py`
- Modify: `agent/openclaw-football-lottery-agent/football-lottery-analyst/tools/openclaw_schema_generator.py`

- [x] **Step 1: 在 `atomic_skills.py` 中引入并封装新工具**
在文件顶部导入 `TodayOffersScraper`，并添加 `get_today_matches_list` 函数。

```python
# existing imports...
import sys
import os
# existing sys.path modifications...
from data_fetch.get_today_offers import TodayOffersScraper

# existing tool instantiations...
offers_scraper = TodayOffersScraper()

def get_today_matches_list(lottery_type: str = "jingcai") -> str:
    """
    [工具7] 获取当天指定彩种的官方在售赛事列表。
    在开始分析前，必须首先调用此工具获取今天可以买哪些比赛，以确定分析的联赛池。
    
    :param lottery_type: 彩种类型，可选 "jingcai", "beidan", "traditional"
    :return: 包含当天赛事基本信息和基础赔率的 JSON 字符串
    """
    try:
        matches = offers_scraper.get_today_offers(lottery_type)
        # 限制返回数量避免 token 超出，真实环境可能需要分页或过滤
        summary = {
            "lottery_type": lottery_type,
            "total_matches": len(matches),
            "matches": matches[:15] # 仅返回前15场作为示例
        }
        return json.dumps(summary, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"获取当天赛事失败: {str(e)}"}, ensure_ascii=False)
```

- [x] **Step 2: 在 `openclaw_schema_generator.py` 中注册新工具**
在 `schema["tools"]` 数组中添加 `get_today_matches_list`。

```python
            {
                "name": "get_today_matches_list",
                "description": "获取当天指定彩种的官方在售赛事列表。在开始分析前，必须首先调用此工具获取今天可以买哪些比赛，以确定分析的联赛池。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lottery_type": {"type": "string", "enum": ["jingcai", "beidan", "traditional"], "description": "彩种类型"}
                    },
                    "required": ["lottery_type"]
                }
            },
```

- [x] **Step 3: 运行 schema 生成脚本**

Run: `python3 agent/openclaw-football-lottery-agent/football-lottery-analyst/tools/openclaw_schema_generator.py`
Expected: 生成成功。

### Task 3: 升级 SOP，实现“赛程获取→玩法识别→组合生成”闭环

**Files:**
- Modify: `agent/openclaw-football-lottery-agent/football-lottery-analyst/prompts/SOP_PROMPT.md`

- [x] **Step 1: 重写 SOP Workflow，强制第一步获取赛程**
修改 `SOP_PROMPT.md` 的 Workflow 部分。

```markdown
# Workflow (Standard Operating Procedure)

## 步骤 1：需求意图识别与赛程获取 (强制第一步)
1. 分析用户的输入。确认目标彩种是【竞彩】、【北单】还是【传统足彩】。
2. **强制动作**：立刻调用 `get_today_matches_list` 工具，传入对应的 `lottery_type`，获取今天该彩种**真实在售**的比赛池。
3. **你的思考**：绝对不能凭空捏造比赛，只能从工具返回的赛事池中挑选比赛进行后续分析。如果用户指定的比赛不在当天的池子里，必须明确告知用户“该比赛今日未开售此彩种”。

## 步骤 2：逐场玩法识别与 EV 评估 (循环操作)
从今日赛程中挑选 2-4 场你认为最有价值的比赛，对每一场执行以下操作：
1. **查基本面**：调用 `get_team_news_and_injuries`。
2. **查水位**：调用 `get_live_odds_and_water_changes`。
3. **算概率**：调用 `calculate_poisson_probability`。
4. **选玩法与定仓**：调用 `evaluate_betting_value`。
   - **核心任务**：你必须为这场比赛识别**最佳玩法**和**备选玩法**。例如：对比“胜平负”和“比分”的 EV，如果比分 2:0 的 EV 远高于单纯的主胜，你必须在心中记录下这个最佳玩法。

## 步骤 3：智能组合与串关生成 (混合过关)
在完成逐场最佳玩法的识别后，你必须将它们组合起来，生成可落单的方案。
1. **竞彩混合过关**：将你挑选出的 2-3 场比赛的【最佳玩法】组合在一起（例如：场次1选胜平负，场次2选让球，场次3选总进球）。
2. 调用 `calculate_jingcai_parlay_prize` 计算这个混合过关组合的真实成本和奖金区间。
3. **容错设计**：你必须主动设计双选容错（如某场比赛同时选主胜和平），或者设计 M串N（如 3串4）来降低风险。

## 步骤 4：(必选) 动态生成数据可视化图表 (多模态输出)
1. 调用 `generate_visual_chart` 工具生成图表（如：`column_chart` 展示比分概率，或 `radar_chart` 展示实力对比）。

# Output Format
你的最终输出必须像一份华尔街的研报，且**抬头必须标明当前分析的彩票种类**：
1. **[彩种标识]**：明确这是针对【竞彩/北单/传统足彩】的专属分析。
2. **今日赛事池过滤**：简述你从今天在售的比赛中挑选了哪几场，为什么挑它们（基于 MLFeatureExtractor 的联赛特征偏好）。
3. **逐场玩法识别**：详细列出每场比赛的【最佳玩法】及【备选玩法】，展示泊松预期进球和真实的 EV。
4. **混合过关组合方案 (Actionable Plan)**：
   - 明确给出 2-3 套可直接去彩票店落单的串关方案（如：激进版 3串1，稳健版 3串4）。
   - 展示每套方案的注数、总成本、最低保本奖金和最高可能奖金。
5. **风控与资金分配**：基于凯利公式的整体仓位建议。
6. **可视化分析 (Chart)**：附上 `generate_visual_chart` 返回的渲染指令。
```

- [x] **Step 2: 确认 SOP 已包含三大核心**
检查文件内容，确保包含了“获取当天比赛”、“玩法识别”、“串关组合推荐”。

### Task 4: 补齐 `get_live_odds_and_water_changes` 对三大彩种的兼容 (Robustness)

**Files:**
- Modify: `agent/openclaw-football-lottery-agent/football-lottery-analyst/tools/atomic_skills.py`

- [x] **Step 1: 修改工具 1，使其能够识别不同彩种的数据源**
虽然 `get_live_odds_and_water_changes` 目前硬编码了澳客竞彩，但在原子工具层面上，我们应提示 LLM 它可以用于获取实时水位，但底层逻辑需要更加鲁棒（这里我们主要做注释更新，因为数据源重构在 Task 1 已经开始了，此工具更多用于盘中监控）。

```python
def get_live_odds_and_water_changes(home_team: str, away_team: str) -> str:
    """
    [工具1] 获取一场比赛实时的赔率水位变动趋势 (主要针对竞彩，北单请参考基础SP)。
    当你需要观察庄家是不是在诱盘(升水/降水)时，调用此工具。
    
    :param home_team: 主队名称 (如: "阿森纳")
    :param away_team: 客队名称 (如: "利物浦")
    :return: 包含初盘、即时盘、水位趋势的 JSON 字符串
    """
    try:
        data = odds_scraper.fetch_live_odds(home_team, away_team)
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"获取赔率失败: {str(e)}"}, ensure_ascii=False)
```