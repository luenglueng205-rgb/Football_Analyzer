---
name: odds-analyzer
description: 赔率分析工具，计算理论概率、庄家抽水、价值投注识别、赔率异常检测
trigger:
  - "赔率分析"
  - "分析赔率"
  - "价值识别"
  - "庄家抽水"
metadata: {"os": ["darwin", "linux"]}
---

# 赔率分析工具

## 功能
1. 计算理论概率和期望值
2. 分析庄家抽水
3. 检测赔率异常
4. 识别价值投注

## 使用示例
```python
from tools.odds_analyzer import analyze_odds

result = analyze_odds(home_odds=1.85, draw_odds=3.40, away_odds=4.20)
```
