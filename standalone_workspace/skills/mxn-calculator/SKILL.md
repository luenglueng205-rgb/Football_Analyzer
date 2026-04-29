---
name: mxn-calculator
description: M串N投注方案计算器，支持自由过关、复式投注、奖金计算
trigger:
  - "串关"
  - "2串1"
  - "3串1"
  - "M串N"
  - "复式投注"
metadata: {"os": ["darwin", "linux"]}
---

# M串N计算器

## 功能
1. 生成M串N投注组合
2. 计算复式投注
3. 奖金优化分析

## 使用示例
```python
from tools.mxn_calculator import generate_parlay

result = generate_parlay(matches=[...], m=2, n=1, stake=100)
```
