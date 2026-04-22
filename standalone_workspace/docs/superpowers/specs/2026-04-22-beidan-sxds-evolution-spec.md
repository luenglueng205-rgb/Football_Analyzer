# Beidan O/U & Odd/Even Matrix Evolution Spec

## Goal
Implement the specialized Beidan 4-Quadrant Matrix (上下盘单双 - Over/Under & Odd/Even) analyzer in the advanced lottery math engine. This is one of the 4 premium strategies identified for AI focus.

## Architecture
1. **Beidan SXDS Calculator**: Create a function `calculate_beidan_sxds_matrix` in `advanced_lottery_math.py` that takes the full Poisson probability matrix as input.
2. **Quadrant Mapping**: It will iterate over the matrix and categorize every possible score into one of four buckets:
   - 上单 (Over & Odd): Total Goals >= 3 AND Total Goals % 2 != 0
   - 上双 (Over & Even): Total Goals >= 3 AND Total Goals % 2 == 0
   - 下单 (Under & Odd): Total Goals < 3 AND Total Goals % 2 != 0
   - 下双 (Under & Even): Total Goals < 3 AND Total Goals % 2 == 0
3. **Output**: Return the exact probabilities for these 4 quadrants to enable AI arbitrage when public betting is heavily skewed.

## Tech Stack
- Python 3.10+
- Existing `advanced_lottery_math.py` module

## Implementation Plan
See `docs/superpowers/plans/2026-04-22-beidan-sxds-evolution.md`
