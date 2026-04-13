---
name: football-lottery-analyst
description: 中国体育彩票足球彩票智能分析技能
version: 1.0.0
author: CodeBuddy Team
tags: [football, lottery, betting, analysis]
triggers:
  - "分析"
  - "赔率"
  - "投注"
  - "竞彩"
  - "足球"
  - "串关"
---

# Skill: 足球彩票分析师

## 功能描述

提供完整的足球彩票分析能力，包括比赛分析、赔率研究、策略制定和风险管理。

## 核心能力

1. **比赛分析**: 分析球队状态、阵容、伤病、历史交锋
2. **赔率分析**: 识别赔率异常、发现价值投注
3. **策略制定**: 生成投注方案、计算串关
4. **风险管理**: 控制仓位、止损机制

## 使用方式

### 斜杠命令
```
/football 分析 [联赛] [主队] vs [客队]
/football 推荐 [玩法类型]
/football 串关 [过关方式]
```

### 自然语言
```
分析今晚的比赛
推荐几场价值投注
生成2串1方案
```

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| league | string | 是 | 联赛名称 |
| home_team | string | 是 | 主队名称 |
| away_team | string | 是 | 客队名称 |
| odds | object | 否 | 赔率数据 |
| budget | number | 否 | 投注预算 |

## 输出格式

```json
{
  "status": "success",
  "data": {
    "match_analysis": { ... },
    "odds_analysis": { ... },
    "recommended_bets": [ ... ],
    "risk_assessment": { ... }
  },
  "confidence": 0.85,
  "warnings": [ ... ]
}
```

## 依赖技能

- odds-analyzer
- mxn-calculator
- smart-selector

## 示例

```javascript
const skill = require('./index.js');

await skill.execute({
  league: '英超',
  home_team: '曼联',
  away_team: '利物浦',
  odds: { home: 1.85, draw: 3.40, away: 4.20 },
  budget: 100
});
```
