# Football Lottery Multi-Agent System v3.0 Pro

符合 **OpenClaw 多Agent规范** 的足球彩票智能分析系统。

## 系统架构 v3.0 Pro

```
FootballLotteryMultiAgentSystem
    │
    ├── OrchestratorAgent (调度中心)
    │       │
    │       ├── ScoutAgent (情报搜集)
    │       ├── AnalystAgent (赔率分析)
    │       ├── StrategistAgent (策略制定)
    │       └── RiskManagerAgent (风险管理)
    │
    ├── ProfessionalAnalyzer (专业分析入口)
    │       │
    │       ├── 竞彩足球专业分析
    │       │       ├── 泊松进球预测
    │       │       ├── 盘口深度分析
    │       │       ├── 半全场预测
    │       │       └── 串关优化
    │       │
    │       ├── 北京单场专业分析
    │       │       ├── SPF/ZJQ/BF/BQC/SXD
    │       │       ├── SP值挖掘
    │       │       └── 串关优化(15关)
    │       │
    │       ├── 传统足彩专业分析
    │       │       ├── 14场深度分析
    │       │       ├── 任选9优化
    │       │       ├── 6场半全场预测
    │       │       ├── 4场进球预测
    │       │       └── 奖池分析
    │       │
    │       └── 跨玩法协同策略
    │               ├── 赔率对比
    │               ├── 套利检测
    │               └── 综合推荐
    │
    ├── Memory (记忆系统)
    │       ├── EpisodicMemory
    │       ├── SemanticMemory
    │       ├── ProceduralMemory
    │       └── Reflector (反思引擎)
    │
    └── Skills (技能模块)
            ├── football-lottery-analyst
            ├── odds-analyzer
            ├── mxn-calculator
            ├── smart-selector
            └── professional_analyzer
```

## 三大玩法全覆盖

### 竞彩足球 (5种玩法)
- ✅ 胜平负 - 基础分析+价值识别
- ✅ 让球胜平负 - 盘口深度分析
- ✅ 总进球 - 泊松预测模型
- ✅ 比分 - 比分矩阵预测
- ✅ 半全场 - 半场概率预测
- ✅ 混合过关 - M串N优化

### 北京单场 (6种玩法 + SP值)
- ✅ 胜平负(含让球) - SPF分析
- ✅ 总进球 - ZJQ分析
- ✅ 比分 - BF分析
- ✅ 半全场 - BQC分析
- ✅ 上下单双 - SXD分析
- ✅ 胜负过关 - SFGG分析
- ✅ SP值挖掘 - 浮动赔率分析
- ✅ 串关优化 - 最高15关

### 传统足彩 (4种玩法)
- ✅ 14场胜负 - 深度分析+胆拖
- ✅ 任选9场 - 智能优化
- ✅ 6场半全场 - 概率预测
- ✅ 4场进球 - 进球预测
- ✅ 奖池分析 - 奖金估算

## OpenClaw 规范符合性 v3.0 Pro

| 规范要求 | 状态 |
|---------|------|
| `AGENTS.md` 主Agent定义 | ✅ |
| 子Agent独立工作空间 | ✅ |
| `openclaw.json` 多Agent配置 | ✅ |
| SKILL.md 技能定义 | ✅ |
| 记忆系统配置 | ✅ |
| 定时任务配置 | ✅ |
| Webhook接口配置 | ✅ |
| 沙箱隔离配置 | ✅ |
| **竞彩足球全面覆盖** | ✅ |
| **北京单场全面覆盖** | ✅ |
| **传统足彩全面覆盖** | ✅ |
| **泊松进球预测模型** | ✅ |
| **盘口深度分析** | ✅ |
| **跨玩法协同策略** | ✅ |
| **专业分析统一入口** | ✅ |

## 目录结构

```
football-lottery-analyst/
├── AGENTS.md                    # 主Agent定义
├── openclaw.json                # OpenClaw配置
├── main.py                      # 主入口
│
├── agents/                      # Agent模块
│   ├── __init__.py
│   ├── base.py                  # Agent基类
│   ├── orchestrator.py          # 调度中心
│   ├── scout.py                 # 情报搜集
│   ├── analyst.py               # 赔率分析
│   ├── strategist.py            # 策略制定
│   ├── risk_manager.py          # 风险管理
│   │
│   └── [agent_id]/              # 各Agent独立工作空间
│       └── workspace/
│           ├── SOUL.md          # Agent灵魂
│           ├── MEMORY.md        # 记忆配置
│           └── USER.md          # 用户偏好
│
├── skills/                      # 技能模块
│   ├── football-lottery-analyst/
│   │   ├── SKILL.md
│   │   ├── index.js
│   │   └── package.json
│   ├── odds-analyzer/
│   ├── mxn-calculator/
│   └── smart-selector/
│
└── data/
    └── memory/                  # 记忆存储
```

## 安装

```bash
# 安装Python依赖
pip install requests beautifulsoup4

# 安装Node.js依赖 (用于Skill)
cd skills/football-lottery-analyst
npm install
```

## 使用方式

### 1. 命令行交互

```bash
python main.py
```

### 2. 单次分析

```bash
python main.py --mode analyze \
    --league 英超 \
    --home 曼联 \
    --away 利物浦 \
    --odds '{"home":1.85,"draw":3.40,"away":4.20}' \
    --budget 100
```

### 3. 快速分析

```bash
python main.py --mode analyze --home 曼联 --away 利物浦 --fast
```

### 4. 查看状态

```bash
python main.py --mode status
```

### 5. 作为模块使用

```python
from main import FootballLotteryMultiAgentSystem

# 初始化
system = FootballLotteryMultiAgentSystem()

# 分析比赛
result = system.analyze(
    league="英超",
    home_team="曼联",
    away_team="利物浦",
    odds={"home": 1.85, "draw": 3.40, "away": 4.20},
    budget=100
)

# 自然语言对话
response = system.chat("分析今晚的比赛")
```

## Agent 职责

| Agent | 职责 | 独立工作空间 |
|-------|------|-------------|
| `orchestrator` | 任务调度和协调 | ✅ |
| `scout` | 情报搜集 | ✅ |
| `analyst` | 赔率分析 | ✅ |
| `strategist` | 策略制定 | ✅ |
| `risk-manager` | 风险管理 | ✅ |

## OpenClaw 集成

### 安装为 OpenClaw Skill

```bash
# 复制到OpenClaw skills目录
cp -r football-lottery-analyst ~/.openclaw/skills/

# 重启OpenClaw
openclaw restart
```

### 多Agent配置

系统支持在 `openclaw.json` 中配置多个独立Agent：

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "default": true,
        "workspace": "agents/main/workspace"
      },
      {
        "id": "scout",
        "workspace": "agents/scout/workspace"
      }
    ]
  }
}
```

### Skill触发词

- 分析
- 赔率
- 投注
- 竞彩
- 足球
- 串关

## 开发

### 创建新Agent

1. 在 `agents/` 下创建目录
2. 编写 `AGENTS.md` 定义
3. 继承 `BaseAgent` 实现业务逻辑
4. 在 `openclaw.json` 注册

### 创建新Skill

1. 在 `skills/` 下创建目录
2. 编写 `SKILL.md` 定义
3. 实现 `index.js` 入口
4. 在 `openclaw.json` 的 `skills.entries` 注册

## License

MIT
