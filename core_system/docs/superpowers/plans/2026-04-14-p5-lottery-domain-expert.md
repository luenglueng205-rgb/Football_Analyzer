# Phase 5: Lottery Domain Expert (全玩法策略路由与知识库) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 赋予系统 100% 掌握竞彩、北单、传统足彩的领域知识，实现从单纯的胜平负预测到全衍生玩法（比分、总进球、半全场等）的智能策略路由。

**Architecture:** 
1. **Math Layer**: 编写 `skills/lottery_math_engine.py`，基于双泊松分布推算 N*M 的比分概率矩阵，并由此折叠出让球、半全场、总进球、上下单双等所有衍生玩法的真实概率。
2. **Knowledge Layer**: 建立 `docs/lottery_rulebook.md`，将三大体彩的硬规则固化，并在 `SyndicateOS` 启动时作为 Context 注入。
3. **Expert Layer**: 修改宽客工具注册表暴露全盘概率引擎，并升级 `JudgeAgent` 的 Prompt，迫使其执行跨玩法比对与串关推荐。

**Tech Stack:** `scipy.stats` (for Poisson), `numpy` (optional, can use pure python), `openai`

---

### Task 1: 编写全景概率引擎 (LotteryMathEngine)

**Files:**
- Create: `skills/lottery_math_engine.py`
- Modify: `requirements.txt` (确保 scipy 安装)

- [ ] **Step 1: 安装 scipy**

```bash
python3 -m pip install scipy --user --break-system-packages
```

- [ ] **Step 2: 编写 LotteryMathEngine 核心类**

```python
import math
from scipy.stats import poisson
from typing import Dict, Any

class LotteryMathEngine:
    """
    全景概率引擎：输入主客队的预期进球数 (xG)，输出包含比分、让球、总进球、半全场等全玩法概率表。
    """
    def __init__(self, max_goals: int = 7):
        self.max_goals = max_goals

    def _build_score_matrix(self, home_xg: float, away_xg: float) -> list:
        matrix = [[0.0 for _ in range(self.max_goals)] for _ in range(self.max_goals)]
        for h in range(self.max_goals):
            for a in range(self.max_goals):
                matrix[h][a] = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)
        return matrix

    def calculate_all_markets(self, home_xg: float, away_xg: float, handicap: float = -1.0) -> Dict[str, Any]:
        matrix = self._build_score_matrix(home_xg, away_xg)
        
        # 1. 胜平负 (W/D/L)
        w, d, l = 0.0, 0.0, 0.0
        # 2. 让球胜平负 (Handicap W/D/L)
        hw, hd, hl = 0.0, 0.0, 0.0
        # 3. 总进球 (Total Goals 0-7+)
        total_goals = {str(i): 0.0 for i in range(8)}
        total_goals["7+"] = 0.0
        # 4. 上下单双 (BD: Over/Under Odd/Even) - 假设 3 球为上盘界限
        shang_dan, shang_shuang, xia_dan, xia_shuang = 0.0, 0.0, 0.0, 0.0
        
        for h in range(self.max_goals):
            for a in range(self.max_goals):
                prob = matrix[h][a]
                
                # W/D/L
                if h > a: w += prob
                elif h == a: d += prob
                else: l += prob
                
                # Handicap (让球)
                adjusted_h = h + handicap
                if adjusted_h > a: hw += prob
                elif adjusted_h == a: hd += prob
                else: hl += prob
                
                # Total Goals
                tg = h + a
                if tg >= 7: total_goals["7+"] += prob
                else: total_goals[str(tg)] += prob
                
                # 上下单双 (北单玩法: 3球以上为上，偶数为双)
                is_shang = (tg >= 3)
                is_shuang = (tg % 2 == 0)
                if is_shang and not is_shuang: shang_dan += prob
                elif is_shang and is_shuang: shang_shuang += prob
                elif not is_shang and not is_shuang: xia_dan += prob
                elif not is_shang and is_shuang: xia_shuang += prob

        # 5. 简单的半全场预估 (Half-Time/Full-Time) - 简化逻辑：半场 xG 大致为全场一半
        ht_w, ht_d, ht_l = 0.0, 0.0, 0.0
        ht_matrix = self._build_score_matrix(home_xg * 0.45, away_xg * 0.45) # 假设半场进球偏少
        for hh in range(self.max_goals):
            for ha in range(self.max_goals):
                p = ht_matrix[hh][ha]
                if hh > ha: ht_w += p
                elif hh == ha: ht_d += p
                else: ht_l += p
                
        # 组装半全场 9 种结果的近似概率 (简单相乘近似，仅供 AI 参考)
        htft = {
            "胜胜": ht_w * w, "胜平": ht_w * d, "胜负": ht_w * l,
            "平胜": ht_d * w, "平平": ht_d * d, "平负": ht_d * l,
            "负胜": ht_l * w, "负平": ht_l * d, "负负": ht_l * l,
        }
        # 归一化 HTFT
        htft_sum = sum(htft.values())
        if htft_sum > 0:
            htft = {k: v / htft_sum for k, v in htft.items()}

        return {
            "match_prob": {"Win": round(w, 4), "Draw": round(d, 4), "Lose": round(l, 4)},
            "handicap_prob": {"Handicap_Win": round(hw, 4), "Handicap_Draw": round(hd, 4), "Handicap_Lose": round(hl, 4)},
            "total_goals": {k: round(v, 4) for k, v in total_goals.items()},
            "bd_up_down": {"上单": round(shang_dan, 4), "上双": round(shang_shuang, 4), "下单": round(xia_dan, 4), "下双": round(xia_shuang, 4)},
            "ht_ft_prob": {k: round(v, 4) for k, v in htft.items()}
        }
```

- [ ] **Step 3: 编写测试脚本验证数学引擎**

```bash
cat << 'EOF' > test_math.py
from skills.lottery_math_engine import LotteryMathEngine

engine = LotteryMathEngine()
# 模拟曼城(2.5 xG) 对阵 弱队(0.5 xG)，让球 -2
res = engine.calculate_all_markets(2.5, 0.5, handicap=-2.0)

print("胜平负:", res["match_prob"])
print("让球(-2):", res["handicap_prob"])
print("总进球:", res["total_goals"])
print("北单上下单双:", res["bd_up_down"])
print("半全场(胜负):", res["ht_ft_prob"]["胜负"])
EOF
python3 test_math.py
```
Expected: PASS (输出各衍生玩法的合理概率)

### Task 2: 注册全景概率引擎至 MCP Tools

**Files:**
- Modify: `tools/mcp_tools.py`
- Modify: `tools/tool_registry_v2.py`

- [ ] **Step 1: 在 `mcp_tools.py` 中暴露接口**

```python
# 找到 tools/mcp_tools.py
from skills.lottery_math_engine import LotteryMathEngine

@ensure_protocol(mock=False, source="math_engine")
def calculate_all_markets(home_xg: float, away_xg: float, handicap: float = -1.0) -> dict:
    """计算竞彩/北单所有衍生玩法(胜平负、让球、总进球、半全场、上下单双)的理论概率。"""
    engine = LotteryMathEngine()
    return engine.calculate_all_markets(home_xg, away_xg, handicap)

# 并在底部的 TOOL_MAPPING 中添加 "calculate_all_markets": calculate_all_markets
```

- [ ] **Step 2: 在 `tool_registry_v2.py` 中注册 Schema**

```python
# 找到 tools/tool_registry_v2.py
class CalculateAllMarketsArgs(BaseModel):
    home_xg: float = Field(..., description="主队预期进球数")
    away_xg: float = Field(..., description="客队预期进球数")
    handicap: float = Field(default=-1.0, description="让球数(例如主让一球为 -1.0，客让一球为 1.0)")

# 在 _TOOLS 中追加
# ToolDefinition("calculate_all_markets", "计算竞彩/北单所有衍生玩法(胜平负、让球、总进球、半全场、上下单双)的理论概率", CalculateAllMarketsArgs, TOOL_MAPPING["calculate_all_markets"]),
```

### Task 3: 建立知识库并注入 SyndicateOS

**Files:**
- Create: `docs/lottery_rulebook.md`
- Modify: `agents/syndicate_os.py`
- Modify: `agents/syndicate_agents.py`

- [ ] **Step 1: 创建知识库文档 `docs/lottery_rulebook.md`**

```bash
mkdir -p docs
cat << 'EOF' > docs/lottery_rulebook.md
# 中国体育彩票三大玩法核心规则库 (The Rulebook)

## 1. 竞彩足球 (JCZQ)
- **支持玩法**: 胜平负、让球胜平负、总进球、比分、半全场。
- **混合过关限制**: 可以将同一场比赛的不同玩法混合串关，但**绝对不允许将同一场比赛的两个不同玩法串在一起**（例如不能串 A场胜平负 + A场总进球，会报同场互斥错误）。
- **单关限制**: 大部分比赛不开售单关胜平负，通常只开售“让球单关”或“总进球单关”。在推荐时，优先考虑串关（2串1，3串1）。
- **让球规则**: 让球数(Handicap)固定为整数（如 -1, +1）。如果在让球后打平，则判定为“让平”。

## 2. 北京单场 (BD)
- **支持玩法**: 胜平负(含让球)、总进球、比分、半全场、上下单双、胜负过关。
- **北单核心特色**: **所有比赛强制带让球**，且让球可能包含小数（如 -0.5, +1.5）。如果让 -0.5 球，则绝无“让平”的可能。
- **上下单双定义**: 上盘=总进球>=3球，下盘=总进球<3球；单=进球数为奇数，双=进球数为偶数。
- **SP 值浮动**: 购买时显示的 SP 值并非最终派奖赔率，最终 SP 会在赛后根据全盘投注量计算。因此，北单不适合计算精确的赛前 EV，只看胜率和预估 SP。
- **支持单关**: 北单所有玩法均支持购买单关。

## 3. 传统足彩 (CTZC)
- **核心玩法**: 14场胜负彩、任选9场 (任九)、6场半全场、4场进球彩。
- **规则特色**: 这是基于“一期奖期”的资金池玩法，并非固定赔率。没有“让球”概念。
- **策略导向**: 必须寻找“冷门”。如果全部买正路（强队赢），即便中了 14 场，奖金可能还不够本金（火锅奖）。必须在策略中刻意挑选 2-3 场高热度强队防平局或爆冷。
EOF
```

- [ ] **Step 2: 修改 `syndicate_os.py` 注入知识库**

```python
# 在 SyndicateOS 类的顶部加载 Rulebook
import os

class SyndicateOS:
    def __init__(self):
        # ... 现有初始化
        rulebook_path = "docs/lottery_rulebook.md"
        if os.path.exists(rulebook_path):
            with open(rulebook_path, "r", encoding="utf-8") as f:
                self.lottery_rulebook = f.read()
        else:
            self.lottery_rulebook = "Rulebook not found."

    # 在 process_match 方法中，将 rulebook 作为 Context 塞给 Judge
    async def process_match(self, home_team: str, away_team: str, lottery_desc: str):
        # ...
        judge_task = f"""
目标赛事：{home_team} vs {away_team}。当前彩种与玩法大类：{lottery_desc}。

【必须遵守的体彩领域知识库 (Rulebook)】
{self.lottery_rulebook}

请主持以下辩论并做出最终的真金白银投资决策...
"""
```

- [ ] **Step 3: 升级 JudgeAgent 的 Prompt (彻底打破胜负偏见)**

在 `syndicate_agents.py` 中修改 `JudgeAgent` 的 Prompt：

```python
        prompt = """你是中国体育彩票的顶级策略专家与风控法官。
你的任务是阅读三大宽客的报告，并结合【体彩领域知识库】做出最聪明的决策。
你的绝对原则：
1. 【打破胜平负偏见】：绝对不要只盯着胜平负！如果发现某场比赛胜平负 EV 过低（蚊子肉），你必须去审视宽客提供的“全景衍生概率”（如总进球、半全场、上下单双），挑选出性价比最高的一个或两个具体玩法！
2. 【严格遵守规则】：如果是竞彩，注意同场互斥；如果是北单，注意让球小数。
3. 如果所有玩法都没有价值，或者宽客分歧巨大，坚决执行 Skip (放弃)。
你拥有唯一的开火权，并在最终报告中明确写出你推荐的【具体玩法】和【赔率/概率理由】。"""
```

### Task 4: 清理测试文件并提交

**Files:**
- None

- [ ] **Step 1: 运行一次测试验证效果**

```bash
python3 run_live_decision.py
```
Expected: 终端日志中，Judge 的最终裁决不再只是说“主胜”，而是会结合规则库提到具体的玩法（例如：“由于主胜赔率过低无投资价值，根据基本面派提供的比分概率，推荐玩法：北单上下单双 - 上双”）。

- [ ] **Step 2: Commit**

```bash
rm test_math.py
git add skills/lottery_math_engine.py docs/lottery_rulebook.md agents/syndicate_os.py agents/syndicate_agents.py tools/mcp_tools.py tools/tool_registry_v2.py
git commit -m "feat(p5): implement lottery domain expert with panoptic math engine and RAG rulebook"
```