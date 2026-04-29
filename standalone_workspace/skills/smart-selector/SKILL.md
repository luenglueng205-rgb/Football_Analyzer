---
name: smart-selector
description: 智能选场引擎，四维分析法筛选价值场次
trigger:
  - "选场"
  - "筛选场次"
  - "推荐比赛"
  - "今天买什么"
metadata: {"os": ["darwin", "linux"]}
---

# 智能选场引擎

## 四维分析法
1. **基本面**: 球队实力、状态、交锋记录
2. **赔率面**: 赔率合理性、庄家倾向
3. **盘口面**: 亚盘解读、水位分析
4. **冷热面**: 市场热度、舆情分析

## 使用示例
```python
from tools.smart_selector import select_matches

recommendations = select_matches(budget=100, risk_level="medium")
```
